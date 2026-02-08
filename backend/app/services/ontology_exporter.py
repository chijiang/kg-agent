# backend/app/services/ontology_exporter.py
"""
Ontology Export Service

Converts the internal PostgreSQL ontology representation to a standard OWL file in Turtle format.
"""

from rdflib import Graph, Literal, RDF, RDFS, OWL, Namespace
from typing import List, Dict, Any

# Define a default namespace for the ontology
BASE_NS = Namespace("http://example.org/ontology#")


class OntologyExporter:
    """Service to export ontology data as OWL/Turtle."""

    def __init__(self):
        self.graph = Graph()
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("base", BASE_NS)

    def export_to_ttl(self, classes: List[Dict], relationships: List[Dict]) -> str:
        """
        Convert internal classes and relationships to Turtle format.

        Args:
            classes: List of dicts with 'name', 'label', 'dataProperties'.
            relationships: List of dicts with 'source', 'type', 'target'.

        Returns:
            str: Turtle formatted string.
        """
        # Add classes
        for cls_data in classes:
            class_uri = BASE_NS[cls_data["name"]]
            self.graph.add((class_uri, RDF.type, OWL.Class))
            if cls_data.get("label"):
                self.graph.add((class_uri, RDFS.label, Literal(cls_data["label"])))

            # Add data properties
            for prop in cls_data.get("dataProperties", []):
                # property format might be "name:string" or just "name"
                prop_name = prop.split(":")[0] if ":" in prop else prop
                prop_uri = BASE_NS[f"prop_{prop_name}"]
                self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
                self.graph.add((prop_uri, RDFS.domain, class_uri))
                # We could add range here if we parsed the type

        # Add object properties (relationships)
        for rel_data in relationships:
            prop_uri = BASE_NS[rel_data["type"]]
            self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop_uri, RDFS.domain, BASE_NS[rel_data["source"]]))
            self.graph.add((prop_uri, RDFS.range, BASE_NS[rel_data["target"]]))

        return self.graph.serialize(format="turtle")
