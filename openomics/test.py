from openomics.multiomics import MultiOmicsData

folder_path = "/Users/jonny/Desktop/PycharmProjects/assn-miRNA-LUAD/data/tcga-assembler/LUAD/"
external_data_path = "/Users/jonny/Desktop/PycharmProjects/assn-miRNA-LUAD/data/external/"
luad_data = MultiOmicsData(cohort_name="LUAD", cohort_folder=folder_path, omics=[
    # "GE",
    "MIR",
    # "LNC",
    # "CNV",
    # "SNP",
    # "PRO"
])

# LNC = luad_data.LNC.get_genes_info()
# print(luad_data.load_data(modalities=["GE", "MIR", "LNC"]))
# print(len(luad_data.LNC.get_genes_list()))
# print(LNC.columns)
# print("LNC transcripts matched", LNC["Rfams"].notnull().sum())
# print(luad_data.MIR.get_genes_info())
# print(luad_data.GE.get_genes_info().T.apply(lambda x: x.nunique(), axis=1))

# table = pd.read_table(luad_data.LNC.lncBase_interactions_file_path)
# print("matching geneName", len(set(LNC.index) & set(table["geneName"])))
# print("matching gene_id", len(set(LNC.index) & set(table["geneId"])))

# print(luad_data.LNC.get_lncRInter_interactions())

# print(LNC.head())