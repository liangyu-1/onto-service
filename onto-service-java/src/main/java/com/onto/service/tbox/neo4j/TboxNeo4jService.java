package com.onto.service.tbox.neo4j;

import com.onto.service.entity.*;

import java.util.List;
import java.util.Optional;

/**
 * TBOX in Neo4j: Domain/Type/Property/Relation/AboxMapping/Logic/Action CRUD.
 */
public interface TboxNeo4jService {

    OntologyDomain createDomain(String domainName, String ddlSql, String createdBy);

    OntologyDomain publishVersion(String domainName, String ddlSql, String createdBy);

    Optional<OntologyDomain> getDomainVersion(String domainName, String version);

    List<OntologyDomain> listDomainVersions(String domainName);

    Optional<OntologyDomain> latestPublished(String domainName);

    OntologyObjectType createObjectType(OntologyObjectType objectType);

    List<OntologyObjectType> listObjectTypes(String domainName, String version);

    OntologyProperty createProperty(OntologyProperty property);

    List<OntologyProperty> listProperties(String domainName, String version, String ownerLabel);

    OntologyRelationship createRelationship(OntologyRelationship relationship);

    List<OntologyRelationship> listRelationships(String domainName, String version);

    OntologyObjectAboxMapping createAboxMapping(OntologyObjectAboxMapping mapping);

    List<OntologyObjectAboxMapping> listAboxMappings(String domainName, String version);

    OntologyLogic createLogic(OntologyLogic logic);

    List<OntologyLogic> listLogic(String domainName, String version);

    OntologyAction createAction(OntologyAction action);

    List<OntologyAction> listActions(String domainName, String version);
}

