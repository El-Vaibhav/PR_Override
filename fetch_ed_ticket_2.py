import requests
import json
import datetime
import re

# --- Jira Config ---
base_url = "https://jira.atlassian.com"
search_url = f"{base_url}/rest/api/2/search"

jql_query = {
    'jql': '''
        project = JRASERVER AND (
            summary ~ "override" OR
            labels in (override, manual-override)
        ) ORDER BY created DESC
    ''',
    'maxResults': 20
}

# --- Elasticsearch Config ---
ELASTIC_URL = "http://localhost:9200/override-logs/_doc"  # Index: override-logs

# --- Helper Function to Extract ED Ticket ---
def extract_ed_ticket(summary):
    match = re.search(r"(ED-\d+)", summary)
    return match.group(1) if match else "N/A"

# --- Fetch from JIRA ---
response = requests.get(
    search_url,
    headers={"Content-Type": "application/json"},
    params=jql_query
)

if response.status_code == 200:
    data = response.json()
    issues = data.get('issues', [])
    
    if not issues:
        print("No override-related tickets found.")
    else:
        print(f"Found {len(issues)} tickets. Sending to Kibana...\n")
        for issue in issues:
            fields = issue['fields']
            summary = fields['summary']
            ed_ticket = extract_ed_ticket(summary)

            # Print nicely formatted output
            print(f"Issue Key   : {issue['key']}")
            print(f"Summary     : {summary}")
            print(f"Status      : {fields['status']['name']}")
            print(f"Reported by : {fields['reporter']['displayName']}")
            print(f"Labels      : {fields.get('labels', [])}")
            print(f"ED Ticket   : {ed_ticket}")
            print('-' * 40)

            # Create JSON log for Kibana
            log_entry = {
                "issue_key": issue['key'],
                "summary": summary,
                "status": fields['status']['name'],
                "reporter": fields['reporter']['displayName'],
                "labels": fields.get('labels', []),
                "ed_ticket": ed_ticket,
                "created": fields['created'],
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }

            # Send to Elasticsearch
            es_response = requests.post(
                ELASTIC_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(log_entry)
            )

            if es_response.status_code in [200, 201]:
                print(f"[✔] Sent {issue['key']} to Kibana.\n")
            else:
                print(f"[✘] Failed to send {issue['key']}: {es_response.status_code}")
                print(es_response.text)

else:
    print(f"Failed to fetch issues: {response.status_code}")
    print(response.text)
