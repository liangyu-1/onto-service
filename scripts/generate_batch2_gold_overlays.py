#!/usr/bin/env python3
"""Generate gold overlays for the second batch of 10 APIs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

APIS = [
    "ably.io_platform",
    "asana.com",
    "box.com",
    "docusign",
    "bitbucket.org",
    "xero_accounting",
    "spotify.com",
    "twilio.com_api",
    "zoom.us",
    "linode.com",
]

# Mapping configuration per API: segment -> object name
SEGMENT_MAP = {
    "ably.io_platform": {
        "channels": "Channel",
        "messages": "Message",
        "presence": "Presence",
        "push": "Push",
        "deviceRegistrations": "DeviceRegistration",
        "channelSubscriptions": "ChannelSubscription",
        "keys": "Key",
        "stats": "Stat",
        "time": "Time",
    },
    "asana.com": {
        "users": "User",
        "user_task_lists": "UserTaskList",
        "workspaces": "Workspace",
        "teams": "Team",
        "projects": "Project",
        "project_templates": "ProjectTemplate",
        "project_briefs": "ProjectBrief",
        "project_statuses": "ProjectStatus",
        "sections": "Section",
        "tasks": "Task",
        "tags": "Tag",
        "stories": "Story",
        "attachments": "Attachment",
        "custom_fields": "CustomField",
        "enum_options": "EnumOption",
        "portfolios": "Portfolio",
        "goals": "Goal",
        "status_updates": "StatusUpdate",
        "webhooks": "Webhook",
        "organization_exports": "OrganizationExport",
        "time_periods": "TimePeriod",
        "events": "Event",
        "jobs": "Job",
        "batch": "Batch",
    },
    "box.com": {
        "files": "File",
        "folders": "Folder",
        "users": "User",
        "groups": "Group",
        "group_memberships": "GroupMembership",
        "collaborations": "Collaboration",
        "comments": "Comment",
        "tasks": "Task",
        "task_assignments": "TaskAssignment",
        "webhooks": "Webhook",
        "file_versions": "FileVersion",
        "metadata_templates": "MetadataTemplate",
        "metadata_cascade_policies": "MetadataCascadePolicy",
        "legal_hold_policies": "LegalHoldPolicy",
        "legal_hold_policy_assignments": "LegalHoldPolicyAssignment",
        "retention_policies": "RetentionPolicy",
        "retention_policy_assignments": "RetentionPolicyAssignment",
        "shield_information_barriers": "ShieldInformationBarrier",
        "sign_requests": "SignRequest",
        "storage_policies": "StoragePolicy",
        "storage_policy_assignments": "StoragePolicyAssignment",
        "web_links": "WebLink",
        "workflows": "Workflow",
        "folder_locks": "FolderLock",
        "device_pinners": "DevicePinner",
        "file_requests": "FileRequest",
        "collections": "Collection",
        "recent_items": "RecentItem",
        "zip_downloads": "ZipDownload",
    },
    "docusign": {
        "accounts": "Account",
        "envelopes": "Envelope",
        "templates": "Template",
        "folders": "Folder",
        "users": "User",
        "groups": "Group",
        "brands": "Brand",
        "billing_plans": "BillingPlan",
        "bulk_send_lists": "BulkSendList",
        "bulk_send_batch": "BulkSendBatch",
        "signing_groups": "SigningGroup",
        "powerforms": "PowerForm",
        "notary": "Notary",
        "workspaces": "Workspace",
        "cloud_storage": "CloudStorage",
        "connect": "ConnectConfiguration",
        "custom_tabs": "CustomTab",
        "permission_profiles": "PermissionProfile",
        "chunked_uploads": "ChunkedUpload",
        "contacts": "Contact",
        "signatures": "Signature",
        "login_information": "User",
        "current_user": "User",
    },
    "bitbucket.org": {
        "repositories": "Repository",
        "workspaces": "Workspace",
        "projects": "Project",
        "pullrequests": "PullRequest",
        "commits": "Commit",
        "branches": "Branch",
        "branch-restrictions": "BranchRestriction",
        "issues": "Issue",
        "pipelines": "Pipeline",
        "snippets": "Snippet",
        "deployments": "Deployment",
        "environments": "DeploymentEnvironment",
        "comments": "Comment",
        "users": "User",
        "teams": "Team",
        "groups": "Group",
        "deploy_keys": "DeployKey",
        "ssh_keys": "SshKey",
        "tags": "Tag",
        "milestones": "Milestone",
        "components": "Component",
        "addon": "Addon",
    },
    "xero_accounting": {
        "Accounts": "Account",
        "Invoices": "Invoice",
        "Contacts": "Contact",
        "BankTransactions": "BankTransaction",
        "Payments": "Payment",
        "CreditNotes": "CreditNote",
        "PurchaseOrders": "PurchaseOrder",
        "Quotes": "Quote",
        "Journals": "Journal",
        "Items": "Item",
        "Employees": "Employee",
        "ExpenseClaims": "ExpenseClaim",
        "ManualJournals": "ManualJournal",
        "Overpayments": "Overpayment",
        "Prepayments": "Prepayment",
        "Receipts": "Receipt",
        "TaxRates": "TaxRate",
        "TrackingCategories": "TrackingCategory",
        "Budgets": "Budget",
        "Reports": "Report",
        "BankTransfers": "BankTransfer",
        "Currencies": "Currency",
        "Attachments": "Attachment",
    },
    "spotify.com": {
        "albums": "Album",
        "artists": "Artist",
        "tracks": "Track",
        "playlists": "Playlist",
        "users": "User",
        "episodes": "Episode",
        "shows": "Show",
        "audiobooks": "Audiobook",
        "chapters": "Chapter",
        "categories": "Category",
        "recommendations": "Recommendation",
        "me": "User",
        "player": "Player",
        "search": "SearchResult",
        "markets": "Market",
    },
    "twilio.com_api": {
        "Accounts": "Account",
        "Addresses": "Address",
        "Applications": "Application",
        "Calls": "Call",
        "Conferences": "Conference",
        "Participants": "ConferenceParticipant",
        "IncomingPhoneNumbers": "IncomingPhoneNumber",
        "Messages": "Message",
        "Recordings": "Recording",
        "Transcriptions": "Transcription",
        "Queues": "Queue",
        "Members": "QueueMember",
        "SipDomains": "SipDomain",
        "SipCredentialLists": "SipCredentialList",
        "SipIpAccessControlLists": "SipIpAccessControlList",
        "UsageTriggers": "UsageTrigger",
        "OutgoingCallerIds": "OutgoingCallerId",
    },
    "zoom.us": {
        "accounts": "Account",
        "users": "User",
        "meetings": "Meeting",
        "webinars": "Webinar",
        "rooms": "Room",
        "groups": "Group",
        "im_groups": "IMGroup",
        "roles": "Role",
        "recordings": "Recording",
        "reports": "Report",
        "tsp": "TSP",
        "phone": "Phone",
        "devices": "Device",
        "h323": "H323Device",
        "sip_trunk": "SipTrunk",
        "common_area_phones": "CommonAreaPhone",
    },
    "linode.com": {
        "account": "Account",
        "users": "User",
        "linodes": "Linode",
        "configs": "LinodeConfig",
        "disks": "LinodeDisk",
        "volumes": "Volume",
        "nodebalancers": "NodeBalancer",
        "configs_nodebalancer": "NodeBalancerConfig",
        "domains": "Domain",
        "records": "DomainRecord",
        "firewalls": "Firewall",
        "images": "Image",
        "stackscripts": "StackScript",
        "longview": "LongviewClient",
        "lke": "KubernetesCluster",
        "types": "LinodeType",
        "regions": "Region",
        "tags": "Tag",
        "networking": "Networking",
        "ips": "IP",
        "support": "SupportTicket",
    },
}

# Object ID field names used in path parameters
PATH_ID_FIELDS = {
    "ably.io_platform": {
        "Channel": "channel_id",
        "Message": "message_id",
        "DeviceRegistration": "device_id",
        "ChannelSubscription": "subscription_id",
        "Key": "key_name",
    },
    "asana.com": {
        "User": "user_id",
        "Workspace": "workspace_id",
        "Team": "team_id",
        "Project": "project_id",
        "ProjectTemplate": "project_template_id",
        "ProjectBrief": "project_brief_id",
        "ProjectStatus": "project_status_id",
        "Section": "section_id",
        "Task": "task_id",
        "Tag": "tag_id",
        "Story": "story_id",
        "Attachment": "attachment_id",
        "CustomField": "custom_field_id",
        "EnumOption": "enum_option_id",
        "Portfolio": "portfolio_id",
        "Goal": "goal_id",
        "StatusUpdate": "status_update_id",
        "Webhook": "webhook_id",
        "OrganizationExport": "organization_export_id",
        "TimePeriod": "time_period_id",
        "Job": "job_id",
    },
    "box.com": {
        "File": "file_id",
        "Folder": "folder_id",
        "User": "user_id",
        "Group": "group_id",
        "GroupMembership": "group_membership_id",
        "Collaboration": "collaboration_id",
        "Comment": "comment_id",
        "Task": "task_id",
        "TaskAssignment": "task_assignment_id",
        "Webhook": "webhook_id",
        "FileVersion": "file_version_id",
        "MetadataTemplate": "template_id",
        "LegalHoldPolicy": "policy_id",
        "RetentionPolicy": "policy_id",
        "SignRequest": "sign_request_id",
        "StoragePolicy": "policy_id",
        "WebLink": "web_link_id",
        "Workflow": "workflow_id",
        "FolderLock": "folder_lock_id",
        "DevicePinner": "device_pinner_id",
        "FileRequest": "file_request_id",
        "Collection": "collection_id",
    },
    "docusign": {
        "Account": "account_id",
        "Envelope": "envelope_id",
        "Template": "template_id",
        "Folder": "folder_id",
        "User": "user_id",
        "Group": "group_id",
        "Brand": "brand_id",
        "BulkSendList": "bulk_send_list_id",
        "BulkSendBatch": "bulk_send_batch_id",
        "SigningGroup": "signing_group_id",
        "PowerForm": "power_form_id",
        "Workspace": "workspace_id",
        "CloudStorage": "cloud_storage_id",
        "ConnectConfiguration": "connect_id",
        "CustomTab": "tab_id",
        "PermissionProfile": "permission_profile_id",
        "ChunkedUpload": "chunked_upload_id",
        "Contact": "contact_id",
        "Signature": "signature_id",
    },
    "bitbucket.org": {
        "Repository": "repo_slug",
        "Workspace": "workspace_id",
        "Project": "project_key",
        "PullRequest": "pull_request_id",
        "Commit": "commit_id",
        "Branch": "branch_name",
        "BranchRestriction": "restriction_id",
        "Issue": "issue_id",
        "Pipeline": "pipeline_uuid",
        "Snippet": "snippet_id",
        "Deployment": "deployment_uuid",
        "DeploymentEnvironment": "environment_uuid",
        "Comment": "comment_id",
        "User": "user_id",
        "Team": "team_name",
        "Group": "group_slug",
        "DeployKey": "key_id",
        "SshKey": "key_id",
        "Tag": "tag_name",
        "Milestone": "milestone_id",
        "Component": "component_id",
    },
    "xero_accounting": {
        "Account": "AccountID",
        "Invoice": "InvoiceID",
        "Contact": "ContactID",
        "BankTransaction": "BankTransactionID",
        "Payment": "PaymentID",
        "CreditNote": "CreditNoteID",
        "PurchaseOrder": "PurchaseOrderID",
        "Quote": "QuoteID",
        "Journal": "JournalID",
        "Item": "ItemID",
        "Employee": "EmployeeID",
        "ExpenseClaim": "ExpenseClaimID",
        "ManualJournal": "ManualJournalID",
        "Overpayment": "OverpaymentID",
        "Prepayment": "PrepaymentID",
        "Receipt": "ReceiptID",
        "TaxRate": "Name",
        "TrackingCategory": "TrackingCategoryID",
        "Budget": "BudgetID",
        "Report": "ReportID",
    },
    "spotify.com": {
        "Album": "album_id",
        "Artist": "artist_id",
        "Track": "track_id",
        "Playlist": "playlist_id",
        "User": "user_id",
        "Episode": "episode_id",
        "Show": "show_id",
        "Audiobook": "audiobook_id",
        "Chapter": "chapter_id",
        "Category": "category_id",
    },
    "twilio.com_api": {
        "Account": "AccountSid",
        "Address": "AddressSid",
        "Application": "ApplicationSid",
        "Call": "CallSid",
        "Conference": "ConferenceSid",
        "ConferenceParticipant": "CallSid",
        "IncomingPhoneNumber": "IncomingPhoneNumberSid",
        "Message": "MessageSid",
        "Recording": "RecordingSid",
        "Transcription": "TranscriptionSid",
        "Queue": "QueueSid",
        "QueueMember": "CallSid",
        "SipDomain": "Sid",
        "SipCredentialList": "Sid",
        "SipIpAccessControlList": "Sid",
        "UsageTrigger": "TriggerSid",
        "OutgoingCallerId": "OutgoingCallerIdSid",
    },
    "zoom.us": {
        "Account": "account_id",
        "User": "user_id",
        "Meeting": "meeting_id",
        "Webinar": "webinar_id",
        "Room": "room_id",
        "Group": "group_id",
        "IMGroup": "im_group_id",
        "Role": "role_id",
        "Recording": "meeting_id",
        "Report": "report_type",
        "TSP": "tsp_id",
        "PhoneUser": "phone_user_id",
        "PhoneNumber": "phone_number_id",
        "Device": "device_id",
    },
    "linode.com": {
        "Account": "id",
        "User": "username",
        "Linode": "linode_id",
        "LinodeConfig": "config_id",
        "LinodeDisk": "disk_id",
        "Volume": "volume_id",
        "NodeBalancer": "nodebalancer_id",
        "NodeBalancerConfig": "config_id",
        "Domain": "domain_id",
        "DomainRecord": "record_id",
        "Firewall": "firewall_id",
        "Image": "image_id",
        "StackScript": "stackscript_id",
        "LongviewClient": "client_id",
        "KubernetesCluster": "cluster_id",
        "LinodeType": "id",
        "Region": "id",
    },
}

# Paths to skip per API (auth, deprecated, fragment-based)
SKIP_PATHS = {
    "ably.io_platform": [],
    "asana.com": ["/events"],
    "box.com": ["/authorize", "/oauth2/token", "/oauth2/revoke", "/shared_items"],
    "docusign": ["/oauth2", "/login_information", "/service_information"],
    "bitbucket.org": ["/addon", "/user"],
    "xero_accounting": ["/connect", "/identity"],
    "spotify.com": ["/oauth"],
    "twilio.com_api": [],
    "zoom.us": ["/oauth"],
    "linode.com": [],
}


def collect_refs(node: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        if "$ref" in node:
            refs.append(node["$ref"].split("/")[-1])
        for v in node.values():
            refs.extend(collect_refs(v))
    elif isinstance(node, list):
        for item in node:
            refs.extend(collect_refs(item))
    return refs


def infer_semantic_role(name: str, ptype: str) -> str:
    norm = name.lower()
    if any(t in norm for t in ["status", "state", "active", "enabled", "archived"]):
        return "state"
    if any(t in norm for t in ["date", "time", "created", "updated", "from", "to", "after", "before"]):
        return "time"
    if any(t in norm for t in ["limit", "offset", "count", "page", "per_page", "max", "min"]):
        return "measure"
    if any(t in norm for t in ["filter", "query", "search", "q", "sort"]):
        return "filter"
    return "payload"


def resolve_bound_objects(api: str, path: str, method: str, op_id: str) -> list[str] | None:
    if path in SKIP_PATHS.get(api, []):
        return None

    seg_map = SEGMENT_MAP[api]
    segments = [s for s in path.split("/") if s]

    # Remove version prefixes
    if segments and segments[0] in ("v2", "v1", "v2010", "api", "2.0"):
        segments = segments[1:]
    if len(segments) >= 2 and segments[0] in ("Accounts",) and segments[1].startswith("{"):
        segments = segments[1:]

    # Asana special: resources named directly
    if api == "asana.com":
        for seg in reversed(segments):
            if seg in seg_map:
                return [seg_map[seg]]
        return None

    # Xero special: resources start with capitalized names like Accounts, Invoices
    if api == "xero_accounting":
        for seg in segments:
            if seg in seg_map:
                return [seg_map[seg]]
        return None

    # Twilio special: /Accounts/{sid}/Calls etc
    if api == "twilio.com_api":
        for seg in reversed(segments):
            if seg in seg_map:
                return [seg_map[seg]]
        # Account as default
        return ["Account"]

    # Default: use last meaningful resource segment
    meaningful = [s for s in segments if not s.startswith("{")]
    if not meaningful:
        return None

    # Relation paths: e.g. /channels/{id}/videos/{id} -> [Channel, Video]
    if len(meaningful) >= 2 and len([s for s in segments if s.startswith("{")]) >= 2:
        parent = seg_map.get(meaningful[-2])
        child = seg_map.get(meaningful[-1])
        if parent and child:
            return [parent, child]

    for seg in reversed(meaningful):
        obj = seg_map.get(seg)
        if obj:
            return [obj]

    return None


def generate_overlay(api: str, path: str, method: str, op: dict[str, Any], bound: list[str]) -> dict[str, Any] | None:
    op_id = op.get("operationId") or f"{method}-{path.replace('/', '-')}"

    kind_map = {"get": "read", "post": "create", "put": "update", "patch": "update", "delete": "delete"}
    kind = kind_map[method.lower()]

    # Adjust kind for known action patterns
    lower_path = path.lower()
    if any(v in lower_path for v in [
        "cancel", "void", "complete", "publish", "accept", "disable", "enable",
        "redeem", "resume", "pause", "archive", "unarchive", "approve", "decline",
        "merge", "lock", "unlock", "restore", "reset", "retry", "capture",
        "follow", "unfollow", "like", "unlike", "join", "link", "unlink",
        "set_album_thumbnail", "copy", "duplicate", "instantiate", "deployments",
    ]):
        if method.lower() in ("post", "put", "patch"):
            kind = "update"
    if any(v in lower_path for v in ["search", "batch-retrieve", "calculate", "query", "events"]):
        kind = "read"
    if any(v in lower_path for v in ["batch-upsert", "batch-change", "batch-create", "replace"]):
        kind = "update"
    if "batch-delete" in lower_path:
        kind = "delete"

    id_fields = PATH_ID_FIELDS.get(api, {})
    params: list[dict[str, Any]] = []

    for param in op.get("parameters", []):
        pname = param.get("name", "")
        pschema = param.get("schema", {})
        ptype = pschema.get("type", "string")
        loc = param.get("in")

        if loc == "path":
            target_obj = bound[0]
            for obj in bound:
                expected = id_fields.get(obj, "id")
                if pname == expected or pname.lower().replace("_", "") == expected.lower().replace("_", ""):
                    target_obj = obj
                    break
                # Fallback: if param name contains object name
                if obj.lower().replace("_", "") in pname.lower().replace("_", ""):
                    target_obj = obj
                    break
            prop = id_fields.get(target_obj, "id")
            params.append({
                "name": pname,
                "location": "path",
                "type": ptype,
                "semantic_role": "identifier",
                "ontology_property": f"{target_obj}.{prop}",
                "required": param.get("required", True),
                "evidence": f"path parameter {pname}",
            })
        elif loc == "query":
            params.append({
                "name": pname,
                "location": "query",
                "type": ptype,
                "semantic_role": infer_semantic_role(pname, ptype),
                "ontology_property": None,
                "required": param.get("required", False),
                "evidence": f"query parameter {pname}",
            })

    body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
    if body:
        body_name = "body"
        if "$ref" in body:
            body_name = body["$ref"].split("/")[-1]
        params.append({
            "name": "body",
            "location": "requestBody",
            "type": "object",
            "semantic_role": "payload",
            "ontology_property": bound[0] if kind in ("create", "update") else None,
            "required": True,
            "evidence": f"requestBody schema {body_name}",
        })

    outputs = [{
        "name": "result",
        "type": "object",
        "semantic_role": "target_object",
        "ontology_property": bound[0],
        "evidence": "200 response",
    }]

    preconditions: list[str] = []
    if kind in ("read", "update", "delete"):
        for pr in params:
            if pr.get("semantic_role") == "identifier":
                prop = pr.get("ontology_property")
                if prop:
                    obj = prop.split(".")[0]
                    preconditions.append(f"{prop} == {pr['name']}")
                    preconditions.append(f"{obj} exists")

    effects: list[str] = []
    if kind == "create":
        effects.append(f"{bound[0]} created")
    elif kind == "update":
        for obj in bound:
            effects.append(f"{obj} updated")
    elif kind == "delete":
        effects.append(f"{bound[0]} deleted")

    overlay_id = f"{api}.{op_id}"
    function_id = re.sub(r"\W+", "_", op_id).strip("_").lower()

    return {
        "overlay_id": overlay_id,
        "endpoint_binding": {
            "method": method.upper(),
            "path": path,
            "operation_id": op_id,
        },
        "candidate_function_id": function_id,
        "operation_kind": kind,
        "bound_object_types": bound,
        "parameter_bindings": params,
        "output_bindings": outputs,
        "preconditions": preconditions,
        "effects": effects,
        "error_contract": [],
        "review_status": "gold",
        "review_note": f"Auto-mapped {kind} operation for {bound}.",
        "evidence": [{"source_type": "openapi", "source_reference": op_id, "claim": f"Maps to {bound}"}],
    }


def main() -> None:
    for api in APIS:
        spec_path = Path(f"dataset/function_layer_benchmarks/raw/apis_guru/specs/{api}.openapi.json")
        if not spec_path.exists():
            print(f"MISSING spec: {spec_path}")
            continue

        spec = json.load(spec_path.open(encoding="utf-8"))
        paths = spec.get("paths", {})

        rows: list[dict[str, Any]] = []
        for path, item in paths.items():
            for method, op in item.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                bound = resolve_bound_objects(api, path, method, op.get("operationId", ""))
                if not bound:
                    continue
                row = generate_overlay(api, path, method, op, bound)
                if row:
                    rows.append(row)

        out_dir = Path(f"dataset/function_layer_benchmarks/generated/apis_guru/reviewed_sample/{api}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "ontology_overlay.gold.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

        print(f"{api}: generated {len(rows)} overlays")


if __name__ == "__main__":
    main()
