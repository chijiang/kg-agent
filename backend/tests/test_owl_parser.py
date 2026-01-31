import pytest
from app.services.owl_parser import OWLParser
from rdflib import Graph, Namespace, RDF, RDFS, OWL


def test_classify_schema_triples():
    # 创建测试图
    g = Graph()
    ex = Namespace("http://example.com/")
    g.add((ex.ClassA, RDF.type, OWL.Class))
    from rdflib import Literal
    g.add((ex.ClassA, RDFS.label, Literal("Class A")))

    parser = OWLParser(g)
    schema, instances = parser.classify_triples()

    assert len(schema) > 0
    assert str(ex.ClassA) in [t.subject for t in schema]
