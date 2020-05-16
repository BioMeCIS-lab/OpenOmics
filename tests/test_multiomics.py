# -*- coding: utf-8 -*-
"""Tests for `openomics` package."""

import os

import pytest

from openomics import MessengerRNA, MicroRNA, LncRNA, Protein, SomaticMutation
from openomics import MultiOmics

cohort_folder_path = "tests/data/TCGA_LUAD"

@pytest.fixture
def generate_TCGA_LUAD_MessengerRNA():
    return MessengerRNA("LUAD", data=os.path.join(cohort_folder_path, "LUAD__geneExp.txt"), transposed=True,
                        columns="GeneSymbol|TCGA", gene_index_by="gene_name")

@pytest.fixture
def generate_TCGA_LUAD_MicroRNA():
    return MicroRNA("LUAD", data=os.path.join(cohort_folder_path, "LUAD__miRNAExp__RPM.txt"), transposed=True,
                    columns="GeneSymbol|TCGA", gene_index_by="gene_name")


@pytest.fixture
def generate_TCGA_LUAD_LncRNA():
    return LncRNA("LUAD", data=os.path.join(cohort_folder_path, "TCGA-rnaexpr.tsv"), transposed=True,
                  columns="Gene_ID|TCGA", gene_index_by="gene_id")


@pytest.fixture
def generate_TCGA_LUAD_SomaticMutation():
    return SomaticMutation("LUAD", data=os.path.join(cohort_folder_path, "LUAD__somaticMutation_geneLevel.txt"),
                           transposed=True, columns="GeneSymbol|TCGA", gene_index_by="gene_name")


@pytest.fixture
def generate_TCGA_LUAD_Protein():
    return Protein("LUAD", data=os.path.join(cohort_folder_path, "protein_RPPA.txt"), transposed=True,
                   columns="GeneSymbol|TCGA", gene_index_by="protein_name")


def test_import_expression_table_size(generate_TCGA_LUAD_MessengerRNA):
    cohort_name = "LUAD"
    luad_data = MultiOmics(cohort_name)
    luad_data.add_clinical_data(
        clinical_data=os.path.join(cohort_folder_path, "nationwidechildrens.org_clinical_patient_luad.txt"))
    luad_data.add_omic(generate_TCGA_LUAD_MessengerRNA)
    luad_data.build_samples()
    print(luad_data.data.keys())
    assert luad_data.data[MessengerRNA.name()].shape == generate_TCGA_LUAD_MessengerRNA.expressions.shape


@pytest.fixture
def generate_TCGA_LUAD(generate_TCGA_LUAD_MessengerRNA, generate_TCGA_LUAD_MicroRNA, generate_TCGA_LUAD_LncRNA,
                       generate_TCGA_LUAD_Protein):
    cohort_name = "LUAD"
    luad_data = MultiOmics(cohort_name)
    luad_data.add_clinical_data(
        clinical_data=os.path.join(cohort_folder_path, "nationwidechildrens.org_clinical_patient_luad.txt"))
    luad_data.add_omic(generate_TCGA_LUAD_MessengerRNA)
    luad_data.add_omic(generate_TCGA_LUAD_MicroRNA)
    luad_data.add_omic(generate_TCGA_LUAD_LncRNA)
    luad_data.add_omic(generate_TCGA_LUAD_Protein)
    return luad_data

def test_TCGA_LUAD_multiomics_transcriptomics(generate_TCGA_LUAD):
    assert all(elem in generate_TCGA_LUAD.get_omics_list() for elem in
               [MessengerRNA.name(), MicroRNA.name(), LncRNA.name(), Protein.name()])
