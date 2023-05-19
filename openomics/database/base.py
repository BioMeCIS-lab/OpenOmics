import copy
import difflib
import logging
import os
import warnings
from abc import ABC, abstractmethod
from os.path import exists, join
from typing import Dict, Union, Any, Callable
from typing import List
from urllib.error import URLError

import dask.dataframe as dd
import filetype
import networkx as nx
import pandas as pd
import tqdm
import validators
from logzero import logger
from typing.io import IO

from ..io.files import get_pkg_data_filename, decompress_file
from ..transforms.agg import get_multi_aggregators, merge_concat
from ..transforms.df import drop_duplicate_columns, match_iterable_keys, has_iterables

__all__ = ['Database', 'Annotatable']

class Database(object):
    """This is a base class used to instantiate an external Database given a a set
    of files from either local files or URLs. When creating a Database class, the
    `load_dataframe()` function is called where the file_resources are used to
    load (Pandas or Dask) DataFrames, then performs data wrangling to yield a
    dataframe at `self.data` . This class also provides an interface for -omics
    tables, e.g. `ExpressionData` , to annotate various annotations,
    expressions, sequences, and disease associations.
    """
    data: pd.DataFrame
    COLUMNS_RENAME_DICT = None  # Needs initialization since subclasses may use this field to rename columns in dataframes.

    def __init__(self, path: str, file_resources: Dict[str, str] = None, index_col: str = None, keys: pd.Series = None,
                 usecols: List[str] = None,
                 col_rename: Dict[str, str] = None, blocksize: int = None, write_uncompressed: bool = False,
                 verbose: bool = False,
                 **kwargs):
        """
        Args:
            path:
                The folder or url path containing the data file resources. If
                url path, the files will be downloaded and cached to the user's
                home folder (at ~/.astropy/).
            file_resources:
                Used to list required files for preprocessing of the
                database. A dictionary where keys are required filenames and
                value are file paths. If None, then the class constructor should
                automatically build the required file resources dict.
            index_col: str of column name, default None.
                 If provided, then set_index() the dataframe at self.data by this
                 column name.
            keys: a pd.Index or a List of str
                If provided, then filter the rows in self.data with `index_col`
                containing these values.
            col_rename (dict): default None,
                A dictionary to rename columns in the data table. If None, then
                automatically load defaults.
            usecols (list, optional): list of strings, default None.
                If provided when loading the dataframes, only use a subset of these
                columns, otherwise load all columns.
            blocksize (int): str, int or None, optional. Default None to
                Number of bytes by which to cut up larger files. Default value
                is computed based on available physical memory and the number
                of cores, up to a maximum of 64MB. Can be a number like 64000000
                or a string like "64MB". If None, a single block is used for
                each file.
            write_uncompressed (bool): default False
                Whether to write the uncompressed file to disk.
            verbose (bool): Default False.
        """
        self.data_path = path
        self.index_col = index_col
        self.keys = keys.compute() if isinstance(keys, (dd.Index, dd.Series)) else keys
        self.usecols = usecols
        self.blocksize = blocksize
        self.verbose = verbose

        self.file_resources = self.load_file_resources(path, file_resources=file_resources,
                                                       write_uncompressed=write_uncompressed, verbose=verbose)

        self.data = self.load_dataframe(self.file_resources, blocksize=blocksize)
        if self.data is not None and col_rename is not None:
            self.data = self.data.rename(columns=col_rename)
            if self.data.index.name in col_rename:
                self.data.index = self.data.index.rename(col_rename[self.data.index.name])

    def __repr__(self):
        out = []
        if hasattr(self, "data") and isinstance(self.data, (pd.DataFrame, dd.DataFrame)):
            out.append("{}: {} {}".format(self.name(), self.data.index.name, self.data.columns.tolist()))
        if hasattr(self, "network") and isinstance(self.network, nx.Graph):
            out.append("{} {}".format(self.network.name, str(self.network)))
        return "\n".join(out)

    def load_file_resources(self, base_path: str, file_resources: Dict[str, str], write_uncompressed: bool = False,
                            verbose=False) -> Dict[str, Any]:
        """For each file in file_resources, download the file if path+file is a
        URL or load from disk if a local path. Additionally unzip or unrar if
        the file is compressed.

        Args:
            base_path (str): The folder or url path containing the data file
                resources. If a url path, the files will be downloaded and
                cached to the user's home folder (at ~/.astropy/).
            file_resources (dict): default None, Used to list required files for
                preprocessing of the database. A dictionary where keys are
                required filenames and value are file paths. If None, then the
                class constructor should automatically build the required file
                resources dict.
            write_uncompressed (bool): default False
                Whether to write the uncompressed file to disk.
            verbose: default False
                Whether to show progress bar of files being loaded
        """
        file_resources_new = copy.copy(file_resources)
        if base_path.startswith("~"):
            base_path = os.path.expanduser(base_path)

        files_prog = tqdm.tqdm(file_resources.items(), desc='Loading file_resources', disable=not verbose)
        for name, filepath in files_prog:
            if filepath.startswith("~"):
                filepath = os.path.expanduser(filepath)

            if verbose:
                files_prog.set_description("Loading file_resources['{}']".format(name))

            # Remote database file URL
            if validators.url(filepath) or validators.url(join(base_path, filepath)):
                try:
                    filepath = get_pkg_data_filename(base_path, filepath)
                    filepath_ext = filetype.guess(filepath)
                except URLError as ue:
                    logger.error(f"{ue}. Skipping {filepath}")
                    continue
                except TypeError as te:
                    filepath_ext = None

            # Local database path
            elif isinstance(filepath, str) and (exists(filepath) or exists(join(base_path, filepath))):
                if not exists(filepath):
                    if exists(join(base_path, filepath)):
                        filepath = join(base_path, filepath)
                    else:
                        warnings.warn(f"`base_path` is a local file directory, so all file_resources must be local. "
                                      f"Cannot use `filepath` = {filepath} with `base_path` = {base_path}")
                        continue
                try:
                    filepath_ext = filetype.guess(filepath)
                except:
                    filepath_ext = None

            else:
                # file_path is an external file outside of `base_path`
                filepath_ext = None

            # Update filepath on uncompressed file
            file_resources_new[name] = filepath

            if filepath_ext:
                filestream, new_filename = decompress_file(filepath, name, file_ext=filepath_ext,
                                                           write_uncompressed=write_uncompressed)
                file_resources_new[new_filename] = filestream

        logging.info(f"{self.name()} file_resources: {file_resources_new}")
        return file_resources_new

    @abstractmethod
    def load_dataframe(self, file_resources: Dict[str, str], blocksize: int = None) -> pd.DataFrame:
        """Handles data preprocessing given the file_resources input, and
        returns a DataFrame.

        Args:
            file_resources (dict): A dict with keys as filenames and values as
                full file path.
            blocksize (int):
        """

    def close(self):
        # Close file readers on file resources (from decompress_file)
        for filename, filepath in self.file_resources.items():
            if isinstance(filepath, IO) or hasattr(filepath, 'close'):
                filepath.close()

    @classmethod
    def name(cls):
        return cls.__name__

    @staticmethod
    def list_databases():
        return DEFAULT_LIBRARIES

    def get_mapper(self, col_a: str, col_b: str) -> pd.Series:
        """
        Create a mapping between values from self.data['col_a'] to values in self.data['col_b']. If either 'col_a' or
        'col_b' contain list-like data, then expand the values in these lists.
        Args:
            col_a ():
            col_b ():

        Returns:
            pd.Series
        """
        df: Union[pd.DataFrame, dd.DataFrame] = self.data.reset_index()[[col_a, col_b]].dropna()
        if has_iterables(df[col_a]):
            df = df.explode(col_a).dropna()
        if has_iterables(df[col_b]):
            df = df.explode(col_b).dropna()

        mapping = df.set_index(col_a)[col_b]

        return mapping

    def get_annotations(self, on: Union[str, List[str]],
                        columns: List[str],
                        agg: str = "unique",
                        agg_for: Dict[str, Union[str, Callable, dd.Aggregation]] = None,
                        keys: pd.Index = None):
        """Returns the Database's DataFrame such that it's indexed by :param
        index:, which then applies a groupby operation and aggregates all other
        columns by concatenating all unique values.

        Args:
            on (str, list): The column name(s) of the DataFrame to group by.
            columns (list): a list of column names to aggregate.
            agg (str): Function to aggregate when there is more than one values
                for each index key value. E.g. ['first', 'last', 'sum', 'mean',
                'size', 'concat'], default 'concat'.
            agg_for (Dict[str, Any]): Bypass the `agg` function for certain
                columns with functions specified in this dict of column names
                and the `agg` function to aggregate for that column.
            keys (pd.Index): The values on the `index` column to
                filter before performing the groupby-agg operations.

        Returns:
            values: An filted-groupby-aggregated dataframe to be used for annotation.
        """
        if not set(columns).issubset(set(self.data.columns).union([self.data.index.name])):
            raise Exception(
                f"The columns argument must be a list such that it's subset of the following columns in the dataframe. "
                f"These columns doesn't exist in `self.data`: {list(set(columns) - set(self.data.columns.tolist()))}"
            )
        elif len(set(columns)) < len(columns):
            raise Exception(f"Duplicate values in `columns`: {columns}")

        # Select df columns including df. However, the `columns` list shouldn't contain the index column
        if on in columns:
            columns = [col for col in columns if col not in on]

        # All columns including `on` and `columns`
        select_cols = columns + ([on] if not isinstance(on, list) else on)
        if self.data.index.name in select_cols:
            # Remove self.data's index_col since we can't select index from the df
            index_col = select_cols.pop(select_cols.index(self.data.index.name))
        else:
            index_col = None

        if isinstance(self.data, pd.DataFrame):
            df = self.data.filter(select_cols, axis="columns")
        elif isinstance(self.data, dd.DataFrame):
            df = self.data[select_cols]
        else:
            raise Exception(f"{self} must have self.data as a pd.DataFrame or dd.DataFrame")

        if index_col and df.index.name != index_col:
            df[index_col] = self.data.index

        # Filter rows in the database if provided `keys` in the `on` column.
        if keys is not None:
            if isinstance(keys, (dd.Series, dd.Index)):
                keys = keys.compute()

            if not has_iterables(keys.head()):
                if on in df.columns:
                    df = df.loc[df[on].isin(keys)]
                elif on == df.index.name:
                    df = df.loc[df.index.isin(keys)]

        df = drop_duplicate_columns(df)

        # Groupby includes column that was in the index
        if on != df.index.name and df.index.name in columns:
            groupby = df.reset_index().groupby(on)

        # Groupby on index
        elif on == df.index.name:
            groupby = df.groupby(lambda x: x)

        # Groupby on other columns
        else:
            groupby = df.groupby(on)

        #  Aggregate by all columns by concatenating unique values
        agg_funcs = get_multi_aggregators(agg, agg_for=agg_for, use_dask=isinstance(df, dd.DataFrame))
        values = groupby.agg({col: agg_funcs[col] for col in columns})

        return values

    def get_expressions(self, index):
        """
        Args:
            index:
        """
        # TODO if index by gene, aggregate medians of transcript-level expressions
        return self.data.groupby(index).median()



class Annotatable(ABC):
    """This abstract class provides an interface for the -omics
    (:class:`Expression`) to annotate its genes list with the external data
    downloaded from various databases. The database will be imported as
    attributes information to the genes's annotations, or interactions between
    the genes.
    """
    SEQUENCE_COL = "sequence"
    DISEASE_ASSOCIATIONS_COL = "disease_associations"

    def get_annotations(self):
        if hasattr(self, "annotations"):
            return self.annotations
        else:
            raise Exception(
                "{} must run initialize_annotations() first.".format(
                    self.name()))

    def get_annotation_expressions(self):
        if hasattr(self, "annotation_expressions"):
            return self.annotation_expressions
        else:
            raise Exception("{} must run annotate_expressions() first.".format(
                self.name()))

    def init_annotations(self, index=None):
        """
        Args:
            index:
            gene_list:
        """
        if hasattr(self, 'annotations') and isinstance(self.annotations,
                                                       (pd.DataFrame, dd.DataFrame)) and not self.annotations.empty:
            warnings.warn("Cannot initialize annotations because annotations already exists.")
            return

        if index is None:
            index = self.get_genes_list()

        self.annotations: pd.DataFrame = pd.DataFrame(index=index)

    def annotate_attributes(self, database: Union[Database, pd.DataFrame], on: Union[str, List[str]],
                            columns: List[str], agg: str = "unique", agg_for: Dict[str, Any] = None,
                            fuzzy_match: bool = False, list_match=False):
        """Performs a left outer join between the annotation and Database's
        DataFrame, on the keys in `on` column. The `on` argument must be column present
        in both DataFrames. If there exists overlapping columns from the join,
        then .fillna() is used to fill NaN values in the old column with non-NaN
        values from the new column.

        Args:
            database (Database): Database which contains an dataframe.
            on (str): The column name which exists in both the annotations and
                Database dataframe to perform the join on.
            columns ([str]): a list of column name to join to the annotation.
            agg (str): Function to aggregate when there is more than one values
                for each index instance. E.g. ['first', 'last', 'sum', 'mean',
                'unique', 'concat'], default 'unique'.
            agg_for (Dict[str, Any]): Bypass the `agg` function for certain
                columns with functions specified in this dict of column names
                and the `agg` function to aggregate for that column.
            fuzzy_match (bool): default False.
                Whether to join the annotation by applying a fuzzy match on the
                string value index with difflib.get_close_matches(). It can be
                slow and thus should only be used sparingly.
            list_match (bool): default False.

        """
        if not hasattr(self, "annotations"):
            raise Exception("Must run .initialize_annotations() on, ", self.__class__.__name__, " first.")

        left_df = self.annotations
        if isinstance(on, str) and on in left_df.columns:
            keys = left_df[on]
        elif isinstance(on, list) and set(on).issubset(left_df.columns):
            keys = left_df[on]
        elif on == left_df.index.name:
            keys = left_df.index
        elif hasattr(left_df.index, 'names') and on in left_df.index.names:
            # MultiIndex
            keys = left_df.index.get_level_values(on)
        else:
            keys = None

        # Get grouped values from `database`
        if isinstance(database, (pd.DataFrame, dd.DataFrame)):
            df = database
            if on == df.index.name and on in df.columns:
                df.pop(on)  # Avoid ambiguous groupby col error
            agg_funcs = get_multi_aggregators(agg=agg, agg_for=agg_for, use_dask=isinstance(df, dd.DataFrame))
            if on == df.index.name or df.index.name in columns:
                groupby = df.reset_index().groupby(on)
            else:
                groupby = df.groupby(on)
            right_df = groupby.agg({col: agg_funcs[col] for col in columns})
        else:
            right_df = database.get_annotations(on, columns=columns, agg=agg, agg_for=agg_for, keys=keys)

        # Match values between `self.annotations[on]` and `values.index`.
        left_on = right_on = on
        orig_keys = left_df.index
        # Fuzzy match between string key values
        if fuzzy_match:
            left_on = right_df.index.map(
                lambda x: difflib.get_close_matches(x, self.annotations.index, n=1)[0])
        # Join on keys of 'list' values if they exist on either `left_keys` or `right_df.index`
        elif list_match:
            left_on, right_on = match_iterable_keys(left=keys, right=right_df.index)

        # Set whether to join on index
        left_index = True if isinstance(left_on, str) and left_df.index.name == left_on else False
        right_index = True if isinstance(right_on, str) and right_df.index.name == right_on else False
        if left_index:
            left_on = None
        if right_index:
            right_on = None

        # Performing join if `on` is already left_df's index
        try:
            if isinstance(left_df, type(right_df)) and left_index:
                merged = left_df.join(right_df, on=on, how="left", rsuffix="_")

            # Perform merge if `on` not index, and choose appropriate merge func depending on dask or pd DF
            else:
                if isinstance(left_df, pd.DataFrame) and isinstance(right_df, dd.DataFrame):
                    merged = dd.merge(left_df, right_df, how="left", left_on=left_on, left_index=left_index,
                                      right_on=right_on, right_index=right_index, suffixes=("", "_"))
                else:
                    merged = left_df.merge(right_df, how="left", left_on=left_on, left_index=left_index,
                                           right_on=right_on, right_index=right_index, suffixes=("", "_"))
        except Exception as e:
            print('left_index', left_index)
            print('left_on', left_on)
            print('right_index', right_index)
            print('right_on', right_on)
            raise e

        if list_match:
            if 'key_0' in merged.columns:
                merged = merged.drop(columns=['key_0'])
            # If `left_on` was a modified keys, then revert the original keys
            merged.index = orig_keys

        # Merge columns if the database DataFrame has overlapping columns with existing column
        duplicate_cols = {col: col.rstrip("_") for col in merged.columns if col.endswith("_")}

        if duplicate_cols:
            new_annotations = merged[list(duplicate_cols.keys())].rename(columns=duplicate_cols)
            logger.info(f"merging {new_annotations.columns}")

            # Combine new values with old values in overlapping columns
            assign_fn = {old_col: merged[old_col].combine(merged[new_col], func=merge_concat) \
                         for new_col, old_col in duplicate_cols.items()}
            merged = merged.assign(**assign_fn)
            # then drop duplicate columns with "_" suffix
            merged = merged.drop(columns=list(duplicate_cols.keys()))

        # Revert back to Pandas DF if not previously a Dask DF
        if isinstance(left_df, pd.DataFrame) and isinstance(merged, dd.DataFrame):
            merged = merged.compute()

        # Assign the new results
        self.annotations = merged

        return self

    def annotate_sequences(self,
                           database,
                           on: Union[str, List[str]],
                           agg="longest",
                           omic=None,
                           **kwargs):
        """Annotate a genes list (based on index) with a dictionary of
        <gene_name: sequence>. If multiple sequences per gene name, then perform
        some aggregation.

        Args:
            database (SequenceDatabase): The database
            on (str): The gene index column name.
            agg (str): The aggregation method, one of ["longest", "shortest", or
                "all"]. Default longest.
            omic (str): Default None. Declare the omic type to fetch sequences
                for.
            **kwargs:
        """
        if omic is None:
            omic = self.name()

        sequences = database.get_sequences(index=on, omic=omic, agg=agg, **kwargs)

        # Map sequences to the keys of `on` columns.
        if type(self.annotations.index) == pd.MultiIndex and self.annotations.index.names in on:
            seqs = self.annotations.index.get_level_values(on).map(sequences)

        elif self.annotations.index.name == on:
            seqs = self.annotations.index.map(sequences)

        elif isinstance(on, list):
            # Index is a multi columns
            seqs = pd.MultiIndex.from_frame(self.annotations.reset_index()[on]).map(sequences)
        else:
            seqs = pd.Index(self.annotations.reset_index()[on]).map(sequences)

        if isinstance(self.annotations, dd.DataFrame) and isinstance(seqs, pd.Series):
            seqs = dd.from_pandas(seqs, npartitions=self.annotations.npartitions)

        self.annotations = self.annotations.assign(**{Annotatable.SEQUENCE_COL: seqs})

        return self

    def annotate_expressions(self, database, index, fuzzy_match=False):
        """

        Args:
            database:
            index:
            fuzzy_match:
        """
        self.annotation_expressions = pd.DataFrame(index=self.annotations.index)

        if self.annotations.index.name == index:
            self.annotation_expressions = self.annotation_expressions.join(
                database.get_expressions(index=index))
        else:
            raise Exception(f"index argument must be one of {database.data.index}")

        return self

    def annotate_interactions(self, database, index):
        """
        Args:
            database (Interactions):
            index (str):
        """
        raise NotImplementedError("Use HeteroNetwork from `moge` package instead")

    def annotate_diseases(self, database, on: Union[str, List[str]]):
        """
        Args:
            database (DiseaseAssociation):
            on (str):
        """
        if on == self.annotations.index.name or (
            hasattr(self.annotations.index, 'names') and on == self.annotations.index.names):
            keys = self.annotations.index
        else:
            keys = self.annotations[on]

        groupby_agg = database.get_disease_assocs(index=on, )

        if isinstance(keys, (pd.DataFrame, pd.Series, pd.Index)):
            if isinstance(keys, pd.DataFrame):
                keys = pd.MultiIndex.from_frame(keys)

            values = keys.map(groupby_agg)

        elif isinstance(keys, dd.DataFrame):
            values = keys.apply(lambda x: groupby_agg.loc[x], axis=1, meta=pd.Series([['']]))
        elif isinstance(keys, dd.Series):
            values = keys.map(groupby_agg)
        else:
            raise Exception()

        self.annotations = self.annotations.assign(**{Annotatable.DISEASE_ASSOCIATIONS_COL: values})

    def set_index(self, new_index):
        """Resets :param new_index: :type new_index: str

        Args:
            new_index:
        """
        self.annotations[new_index].fillna(self.annotations.index.to_series(),
                                           axis=0,
                                           inplace=True)
        self.annotations = self.annotations.reset_index().set_index(new_index)

    def get_rename_dict(self, from_index, to_index):
        """
        Utility function used to retrieve a lookup dictionary to convert from one index to
        another, e.g., gene_id to gene_name, obtained from two columns in the dataframe.

        Returns
            Dict[str, str]: the lookup dictionary.

        Args:
            from_index (str): an index on the DataFrame for key
            to_index:
        """
        if self.annotations.index.name in [from_index, to_index]:
            dataframe = self.annotations.reset_index()
        else:
            dataframe = self.annotations

        dataframe = dataframe[dataframe[to_index].notnull()]
        return pd.Series(dataframe[to_index].values,
                         index=dataframe[from_index]).to_dict()


DEFAULT_LIBRARIES = [
    "10KImmunomes"
    "BioGRID"
    "CCLE"
    "DisGeNET"
    "ENSEMBL"
    "GENCODE"
    "GeneMania"
    "GeneOntology"
    "GlobalBiobankEngine"
    "GTEx"
    "HMDD_miRNAdisease"
    "HPRD_PPI"
    "HUGO_Gene_names"
    "HumanBodyMapLincRNAs"
    "IntAct"
    "lncBase"
    "LNCipedia"
    "LncReg"
    "lncRInter"
    "lncrna2target"
    "lncRNA_data_repository"
    "lncrnadisease"
    "lncRNome"
    "mirbase"
    "miRTarBase"
    "NHLBI_Exome_Sequencing_Project"
    "NONCODE"
    "NPInter"
    "PIRD"
    "RegNetwork"
    "RISE_RNA_Interactions"
    "RNAcentral"
    "StarBase_v2.0"
    "STRING_PPI"
    "TargetScan"
]

