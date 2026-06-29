#!/usr/bin/env python3
"""Build reviewed core ontology/function annotations for selected API systems.

The records produced here are intentionally scoped core subsets. They are
reviewed benchmark seeds, not exhaustive labels for every OpenAPI operation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BASE_RAW = Path("dataset/function_layer_benchmarks/raw/apis_guru/specs")
BASE_OUT = Path("dataset/function_layer_benchmarks/generated/apis_guru")


CONFIGS: dict[str, dict[str, Any]] = {
    "atlassian_jira": {
        "openapi": "atlassian_jira.openapi.json",
        "objects": {
            "Issue": ["id", "key", "summary", "description", "status", "assignee", "project_id", "created", "updated"],
            "Comment": ["id", "body", "author", "created", "updated"],
            "Project": ["id", "key", "name", "description", "lead", "project_type_key"],
        },
        "relations": [("Project", "has_issue", "Issue"), ("Issue", "has_comment", "Comment")],
        "operations": [
            ("create_issue", "POST", "/rest/api/3/issue", "createIssue", "create", "Issue", [], ["Issue.state -> created"]),
            ("get_issue", "GET", "/rest/api/3/issue/{issueIdOrKey}", "getIssue", "read", "Issue", [("issueIdOrKey", "Issue.key")], []),
            ("edit_issue", "PUT", "/rest/api/3/issue/{issueIdOrKey}", "editIssue", "update", "Issue", [("issueIdOrKey", "Issue.key")], ["Issue.updated -> now"]),
            ("delete_issue", "DELETE", "/rest/api/3/issue/{issueIdOrKey}", "deleteIssue", "delete", "Issue", [("issueIdOrKey", "Issue.key")], ["Issue.state -> deleted"]),
            ("list_issue_comments", "GET", "/rest/api/3/issue/{issueIdOrKey}/comment", "getComments", "read", "Comment", [("issueIdOrKey", "Issue.key")], []),
            ("add_issue_comment", "POST", "/rest/api/3/issue/{issueIdOrKey}/comment", "addComment", "create", "Comment", [("issueIdOrKey", "Issue.key")], ["Comment.state -> created"]),
            ("get_issue_comment", "GET", "/rest/api/3/issue/{issueIdOrKey}/comment/{id}", "getComment", "read", "Comment", [("issueIdOrKey", "Issue.key"), ("id", "Comment.id")], []),
            ("update_issue_comment", "PUT", "/rest/api/3/issue/{issueIdOrKey}/comment/{id}", "updateComment", "update", "Comment", [("issueIdOrKey", "Issue.key"), ("id", "Comment.id")], ["Comment.updated -> now"]),
            ("delete_issue_comment", "DELETE", "/rest/api/3/issue/{issueIdOrKey}/comment/{id}", "deleteComment", "delete", "Comment", [("issueIdOrKey", "Issue.key"), ("id", "Comment.id")], ["Comment.state -> deleted"]),
            ("create_project", "POST", "/rest/api/3/project", "createProject", "create", "Project", [], ["Project.state -> created"]),
            ("get_project", "GET", "/rest/api/3/project/{projectIdOrKey}", "getProject", "read", "Project", [("projectIdOrKey", "Project.key")], []),
            ("update_project", "PUT", "/rest/api/3/project/{projectIdOrKey}", "updateProject", "update", "Project", [("projectIdOrKey", "Project.key")], ["Project.updated -> now"]),
            ("delete_project", "DELETE", "/rest/api/3/project/{projectIdOrKey}", "deleteProject", "delete", "Project", [("projectIdOrKey", "Project.key")], ["Project.state -> deleted"]),
        ],
    },
    "box_com": {
        "openapi": "box.com.openapi.json",
        "objects": {
            "File": ["id", "name", "type", "size", "description", "created_at", "modified_at", "parent_id"],
            "Folder": ["id", "name", "type", "description", "created_at", "modified_at", "parent_id"],
            "Comment": ["id", "message", "created_at", "modified_at", "created_by"],
        },
        "relations": [("Folder", "contains_file", "File"), ("Folder", "has_subfolder", "Folder"), ("File", "has_comment", "Comment")],
        "operations": [
            ("upload_file", "POST", "/files/content", "post_files_content", "create", "File", [], ["File.state -> created"]),
            ("get_file", "GET", "/files/{file_id}", "get_files_id", "read", "File", [("file_id", "File.id")], []),
            ("update_file", "PUT", "/files/{file_id}", "put_files_id", "update", "File", [("file_id", "File.id")], ["File.modified_at -> now"]),
            ("restore_file", "POST", "/files/{file_id}", "post_files_id", "update", "File", [("file_id", "File.id")], ["File.state -> restored"]),
            ("delete_file", "DELETE", "/files/{file_id}", "delete_files_id", "delete", "File", [("file_id", "File.id")], ["File.state -> deleted"]),
            ("create_folder", "POST", "/folders", "post_folders", "create", "Folder", [], ["Folder.state -> created"]),
            ("get_folder", "GET", "/folders/{folder_id}", "get_folders_id", "read", "Folder", [("folder_id", "Folder.id")], []),
            ("update_folder", "PUT", "/folders/{folder_id}", "put_folders_id", "update", "Folder", [("folder_id", "Folder.id")], ["Folder.modified_at -> now"]),
            ("delete_folder", "DELETE", "/folders/{folder_id}", "delete_folders_id", "delete", "Folder", [("folder_id", "Folder.id")], ["Folder.state -> deleted"]),
            ("create_comment", "POST", "/comments", "post_comments", "create", "Comment", [], ["Comment.state -> created"]),
            ("get_comment", "GET", "/comments/{comment_id}", "get_comments_id", "read", "Comment", [("comment_id", "Comment.id")], []),
            ("update_comment", "PUT", "/comments/{comment_id}", "put_comments_id", "update", "Comment", [("comment_id", "Comment.id")], ["Comment.modified_at -> now"]),
            ("delete_comment", "DELETE", "/comments/{comment_id}", "delete_comments_id", "delete", "Comment", [("comment_id", "Comment.id")], ["Comment.state -> deleted"]),
        ],
    },
    "docusign": {
        "openapi": "docusign.openapi.json",
        "objects": {
            "Account": ["accountId", "accountName", "status"],
            "Envelope": ["envelopeId", "status", "emailSubject", "createdDateTime", "sentDateTime"],
            "Template": ["templateId", "name", "description", "created", "modified"],
        },
        "relations": [("Account", "has_envelope", "Envelope"), ("Account", "has_template", "Template")],
        "operations": [
            ("list_envelopes", "GET", "/v2.1/accounts/{accountId}/envelopes", "Envelopes_GetEnvelopes", "read", "Envelope", [("accountId", "Account.accountId")], []),
            ("create_envelope", "POST", "/v2.1/accounts/{accountId}/envelopes", "Envelopes_PostEnvelopes", "create", "Envelope", [("accountId", "Account.accountId")], ["Envelope.state -> created"]),
            ("get_envelope", "GET", "/v2.1/accounts/{accountId}/envelopes/{envelopeId}", "Envelopes_GetEnvelope", "read", "Envelope", [("accountId", "Account.accountId"), ("envelopeId", "Envelope.envelopeId")], []),
            ("update_envelope", "PUT", "/v2.1/accounts/{accountId}/envelopes/{envelopeId}", "Envelopes_PutEnvelope", "update", "Envelope", [("accountId", "Account.accountId"), ("envelopeId", "Envelope.envelopeId")], ["Envelope.status -> requested_status"]),
            ("list_templates", "GET", "/v2.1/accounts/{accountId}/templates", "Templates_GetTemplates", "read", "Template", [("accountId", "Account.accountId")], []),
            ("create_template", "POST", "/v2.1/accounts/{accountId}/templates", "Templates_PostTemplates", "create", "Template", [("accountId", "Account.accountId")], ["Template.state -> created"]),
            ("get_template", "GET", "/v2.1/accounts/{accountId}/templates/{templateId}", "Templates_GetTemplate", "read", "Template", [("accountId", "Account.accountId"), ("templateId", "Template.templateId")], []),
            ("update_template", "PUT", "/v2.1/accounts/{accountId}/templates/{templateId}", "Templates_PutTemplate", "update", "Template", [("accountId", "Account.accountId"), ("templateId", "Template.templateId")], ["Template.modified -> now"]),
        ],
    },
    "github_com": {
        "openapi": "github.com.openapi.json",
        "objects": {
            "Repository": ["owner", "repo", "id", "name", "full_name", "description", "private", "default_branch"],
            "Issue": ["issue_number", "id", "title", "body", "state", "assignee", "labels"],
            "PullRequest": ["pull_number", "id", "title", "body", "state", "base", "head"],
        },
        "relations": [("Repository", "has_issue", "Issue"), ("Repository", "has_pull_request", "PullRequest")],
        "operations": [
            ("get_repository", "GET", "/repos/{owner}/{repo}", "repos/get", "read", "Repository", [("owner", "Repository.owner"), ("repo", "Repository.repo")], []),
            ("update_repository", "PATCH", "/repos/{owner}/{repo}", "repos/update", "update", "Repository", [("owner", "Repository.owner"), ("repo", "Repository.repo")], ["Repository.description -> description"]),
            ("delete_repository", "DELETE", "/repos/{owner}/{repo}", "repos/delete", "delete", "Repository", [("owner", "Repository.owner"), ("repo", "Repository.repo")], ["Repository.state -> deleted"]),
            ("list_repository_issues", "GET", "/repos/{owner}/{repo}/issues", "issues/list-for-repo", "read", "Issue", [("owner", "Repository.owner"), ("repo", "Repository.repo")], []),
            ("create_issue", "POST", "/repos/{owner}/{repo}/issues", "issues/create", "create", "Issue", [("owner", "Repository.owner"), ("repo", "Repository.repo")], ["Issue.state -> created"]),
            ("get_issue", "GET", "/repos/{owner}/{repo}/issues/{issue_number}", "issues/get", "read", "Issue", [("owner", "Repository.owner"), ("repo", "Repository.repo"), ("issue_number", "Issue.issue_number")], []),
            ("update_issue", "PATCH", "/repos/{owner}/{repo}/issues/{issue_number}", "issues/update", "update", "Issue", [("owner", "Repository.owner"), ("repo", "Repository.repo"), ("issue_number", "Issue.issue_number")], ["Issue.state -> requested_state"]),
            ("list_pull_requests", "GET", "/repos/{owner}/{repo}/pulls", "pulls/list", "read", "PullRequest", [("owner", "Repository.owner"), ("repo", "Repository.repo")], []),
            ("create_pull_request", "POST", "/repos/{owner}/{repo}/pulls", "pulls/create", "create", "PullRequest", [("owner", "Repository.owner"), ("repo", "Repository.repo")], ["PullRequest.state -> open"]),
            ("get_pull_request", "GET", "/repos/{owner}/{repo}/pulls/{pull_number}", "pulls/get", "read", "PullRequest", [("owner", "Repository.owner"), ("repo", "Repository.repo"), ("pull_number", "PullRequest.pull_number")], []),
            ("update_pull_request", "PATCH", "/repos/{owner}/{repo}/pulls/{pull_number}", "pulls/update", "update", "PullRequest", [("owner", "Repository.owner"), ("repo", "Repository.repo"), ("pull_number", "PullRequest.pull_number")], ["PullRequest.state -> requested_state"]),
        ],
    },
    "sendgrid": {
        "openapi": "sendgrid.openapi.json",
        "objects": {
            "ContactList": ["list_id", "name", "recipient_count"],
            "Recipient": ["recipient_id", "email", "first_name", "last_name", "created_at", "updated_at"],
            "Segment": ["segment_id", "name", "conditions", "recipient_count"],
            "MarketingContact": ["id", "email", "first_name", "last_name"],
        },
        "relations": [("ContactList", "has_recipient", "Recipient"), ("Segment", "filters_recipient", "Recipient")],
        "operations": [
            ("list_contact_lists", "GET", "/contactdb/lists", "GET_contactdb-lists", "read", "ContactList", [], []),
            ("create_contact_list", "POST", "/contactdb/lists", "POST_contactdb-lists", "create", "ContactList", [], ["ContactList.state -> created"]),
            ("get_contact_list", "GET", "/contactdb/lists/{list_id}", "GET_contactdb-lists-list_id", "read", "ContactList", [("list_id", "ContactList.list_id")], []),
            ("update_contact_list", "PATCH", "/contactdb/lists/{list_id}", "PATCH_contactdb-lists-list_id", "update", "ContactList", [("list_id", "ContactList.list_id")], ["ContactList.name -> name"]),
            ("delete_contact_list", "DELETE", "/contactdb/lists/{list_id}", "DELETE_contactdb-lists-list_id", "delete", "ContactList", [("list_id", "ContactList.list_id")], ["ContactList.state -> deleted"]),
            ("list_recipients", "GET", "/contactdb/recipients", "GET_contactdb-recipients", "read", "Recipient", [], []),
            ("add_recipients", "POST", "/contactdb/recipients", "POST_contactdb-recipients", "create", "Recipient", [], ["Recipient.state -> created"]),
            ("get_recipient", "GET", "/contactdb/recipients/{recipient_id}", "GET_contactdb-recipients-recipient_id", "read", "Recipient", [("recipient_id", "Recipient.recipient_id")], []),
            ("delete_recipient", "DELETE", "/contactdb/recipients/{recipient_id}", "DELETE_contactdb-recipients-recipient_id", "delete", "Recipient", [("recipient_id", "Recipient.recipient_id")], ["Recipient.state -> deleted"]),
            ("list_segments", "GET", "/contactdb/segments", "GET_contactdb-segments", "read", "Segment", [], []),
            ("create_segment", "POST", "/contactdb/segments", "POST_contactdb-segments", "create", "Segment", [], ["Segment.state -> created"]),
            ("update_segment", "PATCH", "/contactdb/segments/{segment_id}", "PATCH_contactdb-segments-segment_id", "update", "Segment", [("segment_id", "Segment.segment_id")], ["Segment.conditions -> conditions"]),
            ("delete_segment", "DELETE", "/contactdb/segments/{segment_id}", "DELETE_contactdb-segments-segment_id", "delete", "Segment", [("segment_id", "Segment.segment_id")], ["Segment.state -> deleted"]),
            ("upsert_marketing_contact", "PUT", "/marketing/contacts", "PUT_mc-contacts", "update", "MarketingContact", [], ["MarketingContact.state -> upserted"]),
        ],
    },
    "slack_com": {
        "openapi": "slack.com.openapi.json",
        "objects": {
            "Conversation": ["channel", "name", "is_channel", "is_private", "is_archived", "created"],
            "Message": ["channel", "ts", "text", "user", "thread_ts"],
            "User": ["user", "name", "team_id", "is_admin", "is_owner"],
        },
        "relations": [("Conversation", "has_message", "Message"), ("User", "posts_message", "Message")],
        "operations": [
            ("list_conversations", "GET", "/conversations.list", "conversations_list", "read", "Conversation", [], []),
            ("get_conversation", "GET", "/conversations.info", "conversations_info", "read", "Conversation", [("channel", "Conversation.channel")], []),
            ("create_conversation", "POST", "/conversations.create", "conversations_create", "create", "Conversation", [], ["Conversation.state -> created"]),
            ("archive_conversation", "POST", "/conversations.archive", "conversations_archive", "update", "Conversation", [("channel", "Conversation.channel")], ["Conversation.is_archived -> true"]),
            ("unarchive_conversation", "POST", "/conversations.unarchive", "conversations_unarchive", "update", "Conversation", [("channel", "Conversation.channel")], ["Conversation.is_archived -> false"]),
            ("post_message", "POST", "/chat.postMessage", "chat_postMessage", "create", "Message", [("channel", "Conversation.channel")], ["Message.state -> created"]),
            ("update_message", "POST", "/chat.update", "chat_update", "update", "Message", [("channel", "Conversation.channel"), ("ts", "Message.ts")], ["Message.text -> text"]),
            ("delete_message", "POST", "/chat.delete", "chat_delete", "delete", "Message", [("channel", "Conversation.channel"), ("ts", "Message.ts")], ["Message.state -> deleted"]),
        ],
    },
    "stripe_com": {
        "openapi": "stripe.com.openapi.json",
        "objects": {
            "Customer": ["customer", "id", "email", "name", "description", "created", "deleted"],
            "PaymentIntent": ["intent", "id", "amount", "currency", "customer", "status"],
            "Invoice": ["invoice", "id", "customer", "status", "amount_due", "created"],
        },
        "relations": [("Customer", "has_payment_intent", "PaymentIntent"), ("Customer", "has_invoice", "Invoice")],
        "operations": [
            ("list_customers", "GET", "/v1/customers", "GetCustomers", "read", "Customer", [], []),
            ("create_customer", "POST", "/v1/customers", "PostCustomers", "create", "Customer", [], ["Customer.state -> created"]),
            ("get_customer", "GET", "/v1/customers/{customer}", "GetCustomersCustomer", "read", "Customer", [("customer", "Customer.customer")], []),
            ("update_customer", "POST", "/v1/customers/{customer}", "PostCustomersCustomer", "update", "Customer", [("customer", "Customer.customer")], ["Customer.email -> email"]),
            ("delete_customer", "DELETE", "/v1/customers/{customer}", "DeleteCustomersCustomer", "delete", "Customer", [("customer", "Customer.customer")], ["Customer.deleted -> true"]),
            ("list_payment_intents", "GET", "/v1/payment_intents", "GetPaymentIntents", "read", "PaymentIntent", [], []),
            ("create_payment_intent", "POST", "/v1/payment_intents", "PostPaymentIntents", "create", "PaymentIntent", [], ["PaymentIntent.status -> requires_payment_method"]),
            ("get_payment_intent", "GET", "/v1/payment_intents/{intent}", "GetPaymentIntentsIntent", "read", "PaymentIntent", [("intent", "PaymentIntent.intent")], []),
            ("update_payment_intent", "POST", "/v1/payment_intents/{intent}", "PostPaymentIntentsIntent", "update", "PaymentIntent", [("intent", "PaymentIntent.intent")], ["PaymentIntent.status -> updated"]),
            ("list_invoices", "GET", "/v1/invoices", "GetInvoices", "read", "Invoice", [], []),
            ("create_invoice", "POST", "/v1/invoices", "PostInvoices", "create", "Invoice", [], ["Invoice.status -> draft"]),
            ("get_invoice", "GET", "/v1/invoices/{invoice}", "GetInvoicesInvoice", "read", "Invoice", [("invoice", "Invoice.invoice")], []),
            ("update_invoice", "POST", "/v1/invoices/{invoice}", "PostInvoicesInvoice", "update", "Invoice", [("invoice", "Invoice.invoice")], ["Invoice.status -> updated"]),
            ("delete_invoice", "DELETE", "/v1/invoices/{invoice}", "DeleteInvoicesInvoice", "delete", "Invoice", [("invoice", "Invoice.invoice")], ["Invoice.status -> deleted"]),
        ],
    },
    "xero_accounting": {
        "openapi": "xero_accounting.openapi.json",
        "objects": {
            "Account": ["AccountID", "Code", "Name", "Type", "Status", "UpdatedDateUTC"],
            "Contact": ["ContactID", "ContactNumber", "Name", "EmailAddress", "ContactStatus", "UpdatedDateUTC"],
            "Invoice": ["InvoiceID", "InvoiceNumber", "ContactID", "Type", "Status", "Total", "UpdatedDateUTC"],
        },
        "relations": [("Contact", "has_invoice", "Invoice"), ("Invoice", "uses_account", "Account")],
        "operations": [
            ("list_accounts", "GET", "/Accounts", "getAccounts", "read", "Account", [], []),
            ("create_account", "PUT", "/Accounts", "createAccount", "create", "Account", [], ["Account.Status -> created"]),
            ("get_account", "GET", "/Accounts/{AccountID}", "getAccount", "read", "Account", [("AccountID", "Account.AccountID")], []),
            ("update_account", "POST", "/Accounts/{AccountID}", "updateAccount", "update", "Account", [("AccountID", "Account.AccountID")], ["Account.UpdatedDateUTC -> now"]),
            ("delete_account", "DELETE", "/Accounts/{AccountID}", "deleteAccount", "delete", "Account", [("AccountID", "Account.AccountID")], ["Account.Status -> deleted"]),
            ("list_contacts", "GET", "/Contacts", "getContacts", "read", "Contact", [], []),
            ("create_contacts", "PUT", "/Contacts", "createContacts", "create", "Contact", [], ["Contact.ContactStatus -> created"]),
            ("get_contact", "GET", "/Contacts/{ContactID}", "getContact", "read", "Contact", [("ContactID", "Contact.ContactID")], []),
            ("update_contact", "POST", "/Contacts/{ContactID}", "updateContact", "update", "Contact", [("ContactID", "Contact.ContactID")], ["Contact.UpdatedDateUTC -> now"]),
            ("list_invoices", "GET", "/Invoices", "getInvoices", "read", "Invoice", [], []),
            ("create_invoices", "PUT", "/Invoices", "createInvoices", "create", "Invoice", [], ["Invoice.Status -> created"]),
            ("get_invoice", "GET", "/Invoices/{InvoiceID}", "getInvoice", "read", "Invoice", [("InvoiceID", "Invoice.InvoiceID")], []),
            ("update_invoice", "POST", "/Invoices/{InvoiceID}", "updateInvoice", "update", "Invoice", [("InvoiceID", "Invoice.InvoiceID")], ["Invoice.UpdatedDateUTC -> now"]),
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reviewed core API annotations.")
    parser.add_argument("--api", action="append", choices=sorted(CONFIGS), help="API key to build. Defaults to all configs.")
    parser.add_argument("--base-raw", default=str(BASE_RAW))
    parser.add_argument("--base-out", default=str(BASE_OUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = args.api or sorted(CONFIGS)
    base_raw = Path(args.base_raw)
    base_out = Path(args.base_out)
    summary = []
    for api_key in selected:
        record = build_api(api_key, CONFIGS[api_key], base_raw, base_out)
        summary.append(record)
    print(json.dumps({"built": summary}, ensure_ascii=False, indent=2))


def build_api(api_key: str, config: dict[str, Any], base_raw: Path, base_out: Path) -> dict[str, Any]:
    openapi_path = base_raw / str(config["openapi"])
    openapi = load_json(openapi_path)
    operation_index = collect_operations(openapi)
    output_dir = base_out / api_key
    output_dir.mkdir(parents=True, exist_ok=True)

    ontology = build_ontology(api_key, config, openapi_path)
    overlays = [build_overlay(api_key, config["openapi"], operation_index, op) for op in config["operations"]]
    gold = [to_gold(row) for row in overlays]

    write_json(output_dir / "ontology.reviewed.json", ontology)
    write_jsonl(output_dir / "ontology_overlay.reviewed.jsonl", overlays)
    write_jsonl(output_dir / "gold_functions.reviewed.jsonl", gold)
    return {"api": api_key, "objects": len(ontology["object_types"]), "functions": len(gold)}


def build_ontology(api_key: str, config: dict[str, Any], openapi_path: Path) -> dict[str, Any]:
    objects = []
    for object_id, props in config["objects"].items():
        objects.append(
            {
                "id": object_id,
                "aliases": sorted({object_id, snake_case(object_id), object_id.lower()}),
                "properties": [{"id": prop, "type": infer_type(prop), "aliases": alias_list(prop)} for prop in props],
                "states": ["created", "updated", "deleted"],
                "evidence": [
                    {
                        "source_type": "openapi_core_review",
                        "source_reference": openapi_path.name,
                        "claim": f"{object_id} is a reviewed core object type for {api_key}.",
                    }
                ],
                "review_status": "reviewed",
            }
        )
    return {
        "metadata": {
            "name": f"{api_key}_core_ontology_reviewed_v0",
            "kind": "reviewed_object_ontology",
            "source_openapi": str(openapi_path),
            "scope": "Reviewed core ontology subset for Paper 1 function-layer benchmark annotation.",
            "warning": "This reviewed subset does not cover every schema or operation in the source OpenAPI file.",
        },
        "object_types": objects,
        "relations": [
            {"source": src, "relation": rel, "target": tgt, "review_status": "reviewed"}
            for src, rel, tgt in config.get("relations", [])
        ],
    }


def build_overlay(api_key: str, source_file: str, operation_index: dict[tuple[str, str, str], str], op: tuple[Any, ...]) -> dict[str, Any]:
    function_id, method, path, operation_id, kind, object_id, params, effects = op
    key = (method, path, operation_id)
    if key not in operation_index:
        raise ValueError(f"Operation not found for {api_key}: {method} {path} {operation_id}")
    claim = operation_index[key]
    output_bindings = [] if kind == "delete" else [{"name": snake_case(object_id), "type": "object", "ontology_property": object_id, "evidence": "Successful response returns or affects the bound object type."}]
    return {
        "overlay_id": f"{api_key}.{function_id}",
        "endpoint_binding": {"method": method, "path": path, "operation_id": operation_id},
        "candidate_function_id": function_id,
        "operation_kind": kind,
        "bound_object_types": sorted({object_id, *[prop.split(".", 1)[0] for _, prop in params]}),
        "parameter_bindings": [
            {
                "name": name,
                "location": "path" if f"{{{name}}}" in path else "requestBody",
                "type": "string",
                "semantic_role": "identifier" if "." in prop and prop.rsplit(".", 1)[-1].lower().endswith(("id", "key", "number", "repo", "owner", "customer", "intent", "invoice", "channel", "ts")) else "value",
                "ontology_property": prop,
                "required": f"{{{name}}}" in path,
                "evidence": f"{name} binds to {prop}",
            }
            for name, prop in params
        ],
        "output_bindings": output_bindings,
        "preconditions": [f"{prop} exists" for _, prop in params if f"{{{_}}}" in path],
        "effects": list(effects),
        "error_contract": [],
        "review_status": "reviewed",
        "review_note": "Reviewed core API operation for Paper 1 function-layer benchmark seed.",
        "evidence": [
            {
                "source_type": "openapi",
                "source_reference": f"{source_file}#/paths/{json_pointer_escape(path)}/{method.lower()}",
                "claim": claim or f"{method} {path}",
            }
        ],
    }


def to_gold(overlay: dict[str, Any]) -> dict[str, Any]:
    return {
        "function_id": overlay["candidate_function_id"],
        "endpoint_binding": overlay["endpoint_binding"],
        "operation_kind": overlay["operation_kind"],
        "description": overlay["evidence"][0]["claim"],
        "bound_object_types": overlay["bound_object_types"],
        "inputs": [
            {
                "name": row["name"],
                "type": row["type"],
                "semantic_role": row["semantic_role"],
                "ontology_property": row["ontology_property"],
                "required": row["required"],
            }
            for row in overlay["parameter_bindings"]
        ],
        "outputs": [
            {
                "name": row["name"],
                "type": row["type"],
                "semantic_role": "target_object",
                "ontology_property": row["ontology_property"],
                "required": False,
            }
            for row in overlay["output_bindings"]
        ],
        "preconditions": overlay["preconditions"],
        "effects": overlay["effects"],
        "error_contract": overlay["error_contract"],
        "evidence": overlay["evidence"],
    }


def collect_operations(openapi: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    rows = {}
    for path, path_item in (openapi.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in {"get", "put", "post", "delete", "patch"} or not isinstance(operation, dict):
                continue
            rows[(method.upper(), str(path), str(operation.get("operationId", "")))] = strip_html(
                str(operation.get("summary") or operation.get("description") or "")
            )
    return rows


def infer_type(name: str) -> str:
    lowered = name.lower()
    if lowered.startswith("is_") or lowered in {"deleted", "private"}:
        return "boolean"
    if any(token in lowered for token in ("date", "time", "created", "updated", "modified")):
        return "datetime"
    if any(token in lowered for token in ("count", "amount", "size", "total", "number")):
        return "integer"
    return "string"


def alias_list(prop: str) -> list[str]:
    aliases = {prop, prop.lower(), snake_case(prop)}
    return sorted(aliases)


def snake_case(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.strip("_").lower()


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def json_pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


if __name__ == "__main__":
    main()
