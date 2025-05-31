import requests
from requests.auth import HTTPBasicAuth
import json
import re
from datetime import datetime,timezone
import os


# --- Configuration ---

JIRA_DOMAIN = "https://thoughtspot.atlassian.net"
PROJECT_KEY = "ED"
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")


# ========== STATUSES & QUERY ==========
status1 = "Waiting For Support"
status2 = "In Progress"
request_type_name = "Request Verified+1 Override"

jql_query = (
    f'project={PROJECT_KEY} AND '
    f'(status="{status1}" OR status="{status2}") AND '
    f'"Request Type"="{request_type_name}" '
    f'ORDER BY created DESC'
)

# ========== API CALL ==========
search_url = f"{JIRA_DOMAIN}/rest/api/2/search"
params = {
    "jql": jql_query,
    "maxResults": 1000,
    "fields": "description,customfield_16022,customfield_15010"
}

response = requests.get(
    search_url,
    headers={"Accept": "application/json"},
    auth=HTTPBasicAuth(EMAIL, API_TOKEN),
    params=params
)

if response.status_code != 200:
    print("Failed to fetch issues from JIRA:", response.status_code)
    print(response.text)
    exit(1)

issues = response.json().get("issues", [])

# Store tickets where pipeline link is not None or not empty
tickets_with_pipeline_link = []

# ========== DISPLAY ==========
if issues:
    
    print("\n✅ Tickets with Non-Empty Pipeline Link:\n")
    for issue in issues:
        key = issue['key']
        fields = issue["fields"]
        override_type=fields.get("customfield_15010")
        if override_type['value'] == "restrict-pr": # skip if override_type is other 
            continue
        description = fields.get("description", "")
        pipeline_link = fields.get("customfield_16022")

        if pipeline_link:  # Check if not None or empty
            tickets_with_pipeline_link.append({
                "key": key,
                "description": description,
                "pipeline_link": pipeline_link,
                "override_type": override_type
            })

    # Display filtered tickets
    for ticket in tickets_with_pipeline_link:
        print(f"Ticket: {ticket['key']}")
        print(f"Description: {ticket['description']}")
        print(f"Pipeline Link (customfield_16022): {ticket['pipeline_link']}")
        print(f"Override Type is: {ticket['override_type']['value']}")
        print("-" * 60)

else:
    print("ℹ️ No tickets found for the given criteria.")


# ======= Jenkins part =======
import re

JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")

# Regex to extract job name and build number from the pipeline URL
jenkins_url_pattern = re.compile(
    r'https?://jenkins\.corp\.thoughtspot\.com/job/([^/]+)/(\d+)/?'
)

print("\n📦 Fetching Jenkins Console Output:\n")

# Elasticsearch URL for Kibana ingestion
ELASTIC_URL = "https://es-rke2.corp.thoughtspot.com/ed-override-logs_4/_doc"
valid_tickets = []

for ticket in tickets_with_pipeline_link:
    pipeline_url = ticket['pipeline_link']
    match = jenkins_url_pattern.search(pipeline_url)

    if not match:
        print(f"⚠️ Could not parse Jenkins URL for ticket {ticket['key']}: {pipeline_url}")
        continue

    valid_tickets.append(ticket)

    job_name, build_number = match.groups()
    console_url = f"https://jenkins.corp.thoughtspot.com/job/{job_name}/{build_number}/consoleText"

    print(f"🔍 Fetching console for {ticket['key']} -> {job_name} #{build_number}")
    console_response = requests.get(
        console_url,
        auth=(JENKINS_USER, JENKINS_API_TOKEN)
    )

    if console_response.status_code == 200:
        console_text = console_response.text
        print(f"📄 Console Output for {ticket['key']}:\n")
        print(console_text[:1000])  # Print first 10000 chars to avoid flooding
        print("..." + "\n" + "=" * 80 + "\n")

        payload = {
            "jira_ticket": ticket['key'],
            "console_log_url": console_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        doc_id = f"{ticket['key']}_{build_number}"

        es_response = requests.put(
         f"{ELASTIC_URL}/{doc_id}",
         headers={"Content-Type": "application/json"},
         data=json.dumps(payload)
        )


        if es_response.status_code in [200, 201]:
            print(f"Successfully indexed log URL for {ticket['key']} into Elasticsearch.")
        else:
            print(f"Failed to index log URL for {ticket['key']} (HTTP {es_response.status_code})")
            print(es_response.text)

    else:
        print(f" Failed to fetch console for {ticket['key']} (HTTP {console_response.status_code})")
        print(console_response.text)


tickets_with_pipeline_link = valid_tickets


# ======== ADD KIBANA LINK TO JIRA TICKET COMMENTS ========

KIBANA_DASHBOARD_URL = "https://kibana-rke2.corp.thoughtspot.com/app/discover#/view/6a354880-3d45-11f0-96b6-9d2c4c43041d?_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:now-15m,to:now))&_a=(columns:!(jira_ticket,console_log_url,timestamp),filters:!(),grid:(),hideChart:!f,index:'5877ae52-e0e6-4eca-87fc-96f8f117f1ea',interval:auto,query:(language:kuery,query:''),sort:!(!(timestamp,desc)))"

for ticket in tickets_with_pipeline_link:
    jira_key = ticket['key']
    comment_text = f"🔍 Console log for this override is available in Kibana:\n{KIBANA_DASHBOARD_URL}"

    # Step 1: Fetch existing comments
    get_comments_url = f"{JIRA_DOMAIN}/rest/api/2/issue/{jira_key}/comment"
    get_comments_response = requests.get(
        get_comments_url,
        headers={"Accept": "application/json"},
        auth=HTTPBasicAuth(EMAIL, API_TOKEN)
    )

    if get_comments_response.status_code != 200:
        print(f"Failed to fetch comments for {jira_key} (HTTP {get_comments_response.status_code})")
        continue

    existing_comments = get_comments_response.json().get("comments", [])
    already_commented = any(KIBANA_DASHBOARD_URL in comment.get("body", "") for comment in existing_comments)

    # Step 2: Skip if already commented
    if already_commented:
        print(f"Kibana link already commented on {jira_key}. Skipping.")
        continue

    # Step 3: Post comment
    comment_payload = {"body": comment_text,"public": True }

    comment_payload = {
    "body": comment_text,
    "visibility": {
        "type": "role",
        "value": "Service Desk Customers"} }

    comment_url = f"{JIRA_DOMAIN}/rest/api/2/issue/{jira_key}/comment"

    comment_response = requests.post(
        comment_url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        auth=HTTPBasicAuth(EMAIL, API_TOKEN),
        data=json.dumps(comment_payload)
    )

    if comment_response.status_code == 201:
        print(f"💬 Comment added to JIRA ticket {jira_key}")
    else:
        print(f"❌ Failed to add comment to JIRA ticket {jira_key} (HTTP {comment_response.status_code})")
        print(comment_response.text)

