package com.onto.service.action.admin;

import com.onto.service.entity.OntologyAction;
import com.onto.service.entity.OntologyActionBinding;

import java.util.List;

/**
 * Action 管理服务接口
 */
public interface OntologyActionService {

    OntologyAction createAction(OntologyAction action);

    List<OntologyAction> listActions(String domainName, String version);

    OntologyAction getAction(String domainName, String version, String actionName);

    OntologyAction updateAction(OntologyAction action);

    void deleteAction(String domainName, String version, String actionName);

    OntologyActionBinding createBinding(OntologyActionBinding binding);

    List<OntologyActionBinding> listBindings(String domainName, String version);

    OntologyActionBinding getBinding(String domainName, String version, String actionName, String platformName);

    OntologyActionBinding updateBinding(OntologyActionBinding binding);

    void deleteBinding(String domainName, String version, String actionName, String platformName);
}
