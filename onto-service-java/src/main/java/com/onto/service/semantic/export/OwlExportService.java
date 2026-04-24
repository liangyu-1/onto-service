package com.onto.service.semantic.export;

import com.onto.service.entity.OntologyObjectType;
import com.onto.service.entity.OntologyProperty;
import com.onto.service.entity.OntologyRelationship;
import com.onto.service.semantic.OntologyObjectTypeService;
import com.onto.service.semantic.OntologyPropertyService;
import com.onto.service.semantic.OntologyRelationshipService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Locale;

/**
 * 从 TBOX 生成 RDF/OWL（最小可互通集合，偏向审计归档与 Protégé 打开）
 */
@Service
public class OwlExportService {

    @Autowired
    private OntologyObjectTypeService objectTypeService;

    @Autowired
    private OntologyPropertyService propertyService;

    @Autowired
    private OntologyRelationshipService relationshipService;

    public String exportTurtle(String domainName, String version, String baseIri) {
        String ns = normalizeBaseIri(baseIri, domainName, version);

        List<OntologyObjectType> types = objectTypeService.getObjectTypes(domainName, version);
        List<OntologyRelationship> relationships = relationshipService.getRelationships(domainName, version);

        StringBuilder sb = new StringBuilder(16_384);
        sb.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n");
        sb.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n");
        sb.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n");
        sb.append("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n");
        sb.append("@prefix onto: <").append(ns).append("#> .\n\n");

        // ontology header + a few annotation properties for round-tripping TBOX metadata
        sb.append("onto: a owl:Ontology .\n\n");
        sb.append("onto:aiContext a owl:AnnotationProperty .\n");
        sb.append("onto:valueType a owl:AnnotationProperty .\n");
        sb.append("onto:semanticRole a owl:AnnotationProperty .\n");
        sb.append("onto:isMeasure a owl:AnnotationProperty .\n");
        sb.append("onto:hidden a owl:AnnotationProperty .\n");
        sb.append("onto:semanticAliases a owl:AnnotationProperty .\n");
        sb.append("onto:cardinality a owl:AnnotationProperty .\n");
        sb.append("onto:edgeTable a owl:AnnotationProperty .\n\n");

        // Classes
        for (OntologyObjectType t : types) {
            String c = "onto:" + safeLocalName(t.getLabelName());
            sb.append(c).append(" a owl:Class");
            if (t.getParentLabel() != null && !t.getParentLabel().isBlank()) {
                sb.append(" ;\n  rdfs:subClassOf onto:").append(safeLocalName(t.getParentLabel()));
            }
            String label = firstNonBlank(t.getDisplayName(), t.getLabelName());
            if (label != null) {
                sb.append(" ;\n  rdfs:label ").append(ttlString(label));
            }
            if (isNonBlank(t.getDescription())) {
                sb.append(" ;\n  rdfs:comment ").append(ttlString(t.getDescription()));
            }
            if (isNonBlank(t.getAiContext())) {
                sb.append(" ;\n  onto:aiContext ").append(ttlString(t.getAiContext()));
            }
            sb.append(" .\n\n");

            // Datatype properties owned by this class
            List<OntologyProperty> props = propertyService.getPropertiesByOwner(domainName, version, t.getLabelName());
            for (OntologyProperty p : props) {
                String propIri = "onto:" + safeLocalName(t.getLabelName() + "_" + p.getPropertyName());
                sb.append(propIri).append(" a owl:DatatypeProperty ;\n");
                sb.append("  rdfs:domain ").append(c).append(" ;\n");
                sb.append("  rdfs:range ").append(mapValueTypeToXsd(p.getValueType())).append(" ;\n");
                sb.append("  rdfs:label ").append(ttlString(p.getPropertyName()));
                if (isNonBlank(p.getDescription())) {
                    sb.append(" ;\n  rdfs:comment ").append(ttlString(p.getDescription()));
                }
                if (isNonBlank(p.getAiContext())) {
                    sb.append(" ;\n  onto:aiContext ").append(ttlString(p.getAiContext()));
                }
                if (isNonBlank(p.getValueType())) {
                    sb.append(" ;\n  onto:valueType ").append(ttlString(p.getValueType()));
                }
                if (isNonBlank(p.getSemanticRole())) {
                    sb.append(" ;\n  onto:semanticRole ").append(ttlString(p.getSemanticRole()));
                }
                if (p.getIsMeasure() != null) {
                    sb.append(" ;\n  onto:isMeasure ").append(p.getIsMeasure() ? "true" : "false");
                }
                if (p.getHidden() != null) {
                    sb.append(" ;\n  onto:hidden ").append(p.getHidden() ? "true" : "false");
                }
                if (p.getSemanticAliases() != null && !p.getSemanticAliases().isEmpty()) {
                    sb.append(" ;\n  onto:semanticAliases ").append(ttlString(String.join(",", p.getSemanticAliases())));
                }
                sb.append(" .\n\n");
            }
        }

        // Object properties (relationships)
        for (OntologyRelationship r : relationships) {
            String relIri = "onto:" + safeLocalName(r.getLabelName());
            sb.append(relIri).append(" a owl:ObjectProperty ;\n");
            sb.append("  rdfs:domain onto:").append(safeLocalName(r.getSourceLabel())).append(" ;\n");
            sb.append("  rdfs:range onto:").append(safeLocalName(r.getTargetLabel())).append(" ;\n");
            sb.append("  rdfs:label ").append(ttlString(r.getLabelName()));
            if (isNonBlank(r.getAiContext())) {
                sb.append(" ;\n  onto:aiContext ").append(ttlString(r.getAiContext()));
            }
            if (isNonBlank(r.getCardinality())) {
                sb.append(" ;\n  onto:cardinality ").append(ttlString(r.getCardinality()));
            }
            if (isNonBlank(r.getEdgeTable())) {
                sb.append(" ;\n  onto:edgeTable ").append(ttlString(r.getEdgeTable()));
            }
            sb.append(" .\n\n");
        }

        return sb.toString();
    }

    private static String normalizeBaseIri(String baseIri, String domainName, String version) {
        String iri = (baseIri == null || baseIri.isBlank())
                ? ("urn:onto:" + domainName + ":" + version)
                : baseIri.trim();
        // Strip trailing fragment/hash for stable ns + '#'
        while (iri.endsWith("#") || iri.endsWith("/")) {
            iri = iri.substring(0, iri.length() - 1);
        }
        return iri;
    }

    private static String safeLocalName(String raw) {
        if (raw == null || raw.isBlank()) return "Unnamed";
        String s = raw.trim();
        StringBuilder out = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (Character.isLetterOrDigit(ch) || ch == '_' || ch == '-') {
                out.append(ch);
            } else {
                out.append('_');
            }
        }
        // Turtle prefixed names cannot start with digit in some tools; prefix with '_' if needed
        if (out.length() > 0 && Character.isDigit(out.charAt(0))) {
            out.insert(0, '_');
        }
        return out.toString();
    }

    private static String mapValueTypeToXsd(String valueType) {
        if (valueType == null) return "xsd:string";
        String t = valueType.trim().toUpperCase(Locale.ROOT);
        return switch (t) {
            case "DOUBLE", "FLOAT", "DECIMAL" -> "xsd:double";
            case "INT", "INTEGER", "BIGINT", "LONG" -> "xsd:long";
            case "BOOLEAN", "BOOL" -> "xsd:boolean";
            case "TIMESTAMP", "DATETIME" -> "xsd:dateTime";
            default -> "xsd:string";
        };
    }

    private static boolean isNonBlank(String s) {
        return s != null && !s.isBlank();
    }

    private static String firstNonBlank(String... ss) {
        for (String s : ss) {
            if (isNonBlank(s)) return s;
        }
        return null;
    }

    private static String ttlString(String s) {
        String esc = s
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\r", "\\r")
                .replace("\n", "\\n");
        return "\"" + esc + "\"";
    }
}

