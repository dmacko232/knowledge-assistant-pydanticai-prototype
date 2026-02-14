#!/usr/bin/env python3
"""
Data Analysis Script for Northwind Commerce Knowledge Base
Analyzes data/raw and outputs reports to data_analysis/outputs
"""

import json
import csv
import os
from pathlib import Path
from datetime import datetime as dt, timedelta
from collections import defaultdict, Counter
import re

def load_directory_data():
    """Load employee directory from JSON"""
    with open('../data/raw/structured/directory.json', 'r') as f:
        return json.load(f)

def load_kpi_catalog():
    """Load KPI catalog from CSV"""
    kpis = []
    with open('../data/raw/structured/kpi_catalog.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            kpis.append(row)
    return kpis

def analyze_documents():
    """Analyze all markdown documents"""
    docs_path = Path('../data/raw/documents')
    docs_analysis = {
        'domain': [],
        'policies': [],
        'runbooks': []
    }

    for category in docs_analysis.keys():
        category_path = docs_path / category
        if category_path.exists():
            for doc_file in category_path.glob('*.md'):
                with open(doc_file, 'r') as f:
                    content = f.read()

                # Extract metadata
                lines = content.split('\n')
                title = lines[0].replace('#', '').strip() if lines else doc_file.stem

                # Find last updated date
                last_updated = None
                for line in lines[:10]:  # Check first 10 lines
                    if 'last updated' in line.lower():
                        date_match = re.search(r'\d{4}-\d{2}-\d{2}', line)
                        if date_match:
                            last_updated = date_match.group(0)
                        break

                docs_analysis[category].append({
                    'filename': doc_file.name,
                    'title': title,
                    'last_updated': last_updated,
                    'word_count': len(content.split()),
                    'line_count': len(lines),
                    'has_links': bool(re.search(r'\[.*?\]\(.*?\)', content)),
                    'has_code_blocks': '```' in content
                })

    return docs_analysis

def analyze_teams_and_ownership(directory_data, kpi_data):
    """Analyze team composition and ownership"""
    teams = defaultdict(list)
    roles = Counter()
    timezones = Counter()

    for person in directory_data:
        teams[person['team']].append(person)
        roles[person['role']] += 1
        timezones[person['timezone']] += 1

    # KPI ownership
    kpi_owners = Counter()
    for kpi in kpi_data:
        kpi_owners[kpi['owner_team']] += 1

    return {
        'teams': dict(teams),
        'team_sizes': {team: len(members) for team, members in teams.items()},
        'roles': dict(roles),
        'timezones': dict(timezones),
        'kpi_ownership': dict(kpi_owners)
    }

def analyze_kpis(kpi_data):
    """Detailed KPI analysis"""
    analysis = {
        'total_kpis': len(kpi_data),
        'by_owner': defaultdict(list),
        'by_source': defaultdict(list),
        'update_recency': [],
        'data_sources': set()
    }

    for kpi in kpi_data:
        analysis['by_owner'][kpi['owner_team']].append(kpi['kpi_name'])
        analysis['by_source'][kpi['primary_source']].append(kpi['kpi_name'])
        analysis['data_sources'].add(kpi['primary_source'])

        if kpi['last_updated']:
            analysis['update_recency'].append({
                'kpi': kpi['kpi_name'],
                'last_updated': kpi['last_updated'],
                'owner': kpi['owner_team']
            })

    # Convert defaultdicts to regular dicts
    analysis['by_owner'] = dict(analysis['by_owner'])
    analysis['by_source'] = dict(analysis['by_source'])
    analysis['data_sources'] = sorted(list(analysis['data_sources']))
    analysis['update_recency'].sort(key=lambda x: x['last_updated'], reverse=True)

    return analysis

def generate_overview_report(directory_data, kpi_data, docs_analysis):
    """Generate overview report"""
    report = []
    report.append("# Northwind Commerce Knowledge Base - Overview Analysis")
    report.append(f"\nGenerated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append("## Dataset Summary\n")
    report.append(f"- **Total Employees:** {len(directory_data)}")
    report.append(f"- **Total KPIs:** {len(kpi_data)}")
    report.append(f"- **Domain Documents:** {len(docs_analysis['domain'])}")
    report.append(f"- **Policy Documents:** {len(docs_analysis['policies'])}")
    report.append(f"- **Runbook Documents:** {len(docs_analysis['runbooks'])}")
    report.append(f"- **Total Documents:** {sum(len(docs) for docs in docs_analysis.values())}\n")

    report.append("## Document Categories\n")
    for category, docs in docs_analysis.items():
        report.append(f"### {category.title()}")
        for doc in docs:
            report.append(f"- [{doc['title']}](../../data/raw/documents/{category}/{doc['filename']})")
            report.append(f"  - Last updated: {doc['last_updated'] or 'Unknown'}")
            report.append(f"  - Size: {doc['word_count']} words, {doc['line_count']} lines")
        report.append("")

    return '\n'.join(report)

def generate_team_analysis(team_data):
    """Generate team and ownership analysis"""
    report = []
    report.append("# Team and Ownership Analysis\n")
    report.append(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append("## Team Composition\n")
    report.append("| Team | Size | Members |")
    report.append("|------|------|---------|")
    for team, members in sorted(team_data['teams'].items(), key=lambda x: len(x[1]), reverse=True):
        member_names = ', '.join([m['name'] for m in members])
        report.append(f"| {team} | {len(members)} | {member_names} |")
    report.append("")

    report.append("## KPI Ownership by Team\n")
    report.append("| Team | KPI Count |")
    report.append("|------|-----------|")
    for team, count in sorted(team_data['kpi_ownership'].items(), key=lambda x: x[1], reverse=True):
        report.append(f"| {team} | {count} |")
    report.append("")

    report.append("## Geographic Distribution\n")
    report.append("| Timezone | Count |")
    report.append("|----------|-------|")
    for tz, count in sorted(team_data['timezones'].items(), key=lambda x: x[1], reverse=True):
        report.append(f"| {tz} | {count} |")
    report.append("")

    report.append("## Role Distribution\n")
    report.append("| Role | Count |")
    report.append("|------|-------|")
    for role, count in sorted(team_data['roles'].items(), key=lambda x: x[1], reverse=True):
        report.append(f"| {role} | {count} |")
    report.append("")

    return '\n'.join(report)

def generate_kpi_analysis(kpi_analysis):
    """Generate KPI analysis report"""
    report = []
    report.append("# KPI Analysis Report\n")
    report.append(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append(f"## Overview\n")
    report.append(f"- **Total KPIs:** {kpi_analysis['total_kpis']}")
    report.append(f"- **Unique Data Sources:** {len(kpi_analysis['data_sources'])}\n")

    report.append("## KPIs by Owner Team\n")
    for owner, kpis in sorted(kpi_analysis['by_owner'].items(), key=lambda x: len(x[1]), reverse=True):
        report.append(f"### {owner} ({len(kpis)} KPIs)")
        for kpi in kpis:
            report.append(f"- {kpi}")
        report.append("")

    report.append("## Data Sources\n")
    report.append("| Data Source | KPI Count | KPIs |")
    report.append("|-------------|-----------|------|")
    for source, kpis in sorted(kpi_analysis['by_source'].items(), key=lambda x: len(x[1]), reverse=True):
        kpi_list = ', '.join(kpis)
        report.append(f"| {source} | {len(kpis)} | {kpi_list} |")
    report.append("")

    report.append("## Update Recency\n")
    report.append("| KPI | Last Updated | Owner |")
    report.append("|-----|--------------|-------|")
    for item in kpi_analysis['update_recency']:
        report.append(f"| {item['kpi']} | {item['last_updated']} | {item['owner']} |")
    report.append("")

    return '\n'.join(report)

def generate_document_metadata_analysis(docs_analysis):
    """Generate document metadata analysis"""
    report = []
    report.append("# Document Metadata Analysis\n")
    report.append(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_docs = []
    for category, docs in docs_analysis.items():
        for doc in docs:
            doc['category'] = category
            all_docs.append(doc)

    report.append("## All Documents by Update Date\n")
    report.append("| Document | Category | Last Updated | Size |")
    report.append("|----------|----------|--------------|------|")

    # Sort by last_updated (most recent first)
    sorted_docs = sorted(all_docs, key=lambda x: x['last_updated'] or '1900-01-01', reverse=True)
    for doc in sorted_docs:
        report.append(f"| {doc['title']} | {doc['category']} | {doc['last_updated'] or 'Unknown'} | {doc['word_count']} words |")
    report.append("")

    report.append("## Document Statistics\n")
    total_words = sum(doc['word_count'] for doc in all_docs)
    total_lines = sum(doc['line_count'] for doc in all_docs)
    docs_with_links = sum(1 for doc in all_docs if doc['has_links'])
    docs_with_code = sum(1 for doc in all_docs if doc['has_code_blocks'])

    report.append(f"- **Total Word Count:** {total_words:,}")
    report.append(f"- **Total Line Count:** {total_lines:,}")
    report.append(f"- **Documents with Links:** {docs_with_links}/{len(all_docs)}")
    report.append(f"- **Documents with Code Blocks:** {docs_with_code}/{len(all_docs)}")
    report.append(f"- **Average Document Size:** {total_words//len(all_docs)} words\n")

    return '\n'.join(report)

def generate_policy_compliance_report(docs_analysis, kpi_data):
    """Generate policy and compliance observations"""
    report = []
    report.append("# Policy and Compliance Analysis\n")
    report.append(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append("## Policy Documents\n")
    for doc in docs_analysis['policies']:
        report.append(f"### {doc['title']}")
        report.append(f"- **File:** {doc['filename']}")
        report.append(f"- **Last Updated:** {doc['last_updated'] or 'Unknown'}")
        report.append(f"- **Size:** {doc['word_count']} words\n")

    report.append("## Data Freshness Observations\n")

    # Check KPI update dates
    current_date = dt.now()
    old_kpis = []
    recent_kpis = []

    for kpi in kpi_data:
        if kpi['last_updated']:
            update_date = dt.strptime(kpi['last_updated'], '%Y-%m-%d')
            days_old = (current_date - update_date).days

            if days_old > 60:
                old_kpis.append((kpi['kpi_name'], kpi['last_updated'], days_old))
            elif days_old < 30:
                recent_kpis.append((kpi['kpi_name'], kpi['last_updated'], days_old))

    if old_kpis:
        report.append(f"### KPIs Not Updated in 60+ Days ({len(old_kpis)})")
        for kpi_name, last_updated, days in sorted(old_kpis, key=lambda x: x[2], reverse=True):
            report.append(f"- **{kpi_name}** - Last updated {last_updated} ({days} days ago)")
        report.append("")

    if recent_kpis:
        report.append(f"### Recently Updated KPIs (<30 days) ({len(recent_kpis)})")
        for kpi_name, last_updated, days in sorted(recent_kpis, key=lambda x: x[2]):
            report.append(f"- **{kpi_name}** - Last updated {last_updated} ({days} days ago)")
        report.append("")

    # Check document dates
    all_docs = []
    for category, docs in docs_analysis.items():
        all_docs.extend(docs)

    old_docs = []
    for doc in all_docs:
        if doc['last_updated']:
            try:
                update_date = dt.strptime(doc['last_updated'], '%Y-%m-%d')
                days_old = (current_date - update_date).days
                if days_old > 60:
                    old_docs.append((doc['title'], doc['last_updated'], days_old))
            except:
                pass

    if old_docs:
        report.append(f"### Documents Not Updated in 60+ Days ({len(old_docs)})")
        for title, last_updated, days in sorted(old_docs, key=lambda x: x[2], reverse=True):
            report.append(f"- **{title}** - Last updated {last_updated} ({days} days ago)")
        report.append("")

    report.append("## Recommendations\n")
    report.append("1. Review and update KPIs and documents that haven't been modified in 60+ days")
    report.append("2. Ensure all policy documents have clear version numbers and effective dates")
    report.append("3. Consider adding version control metadata to all documents")
    report.append("4. Establish a regular review cycle for all knowledge base content\n")

    return '\n'.join(report)

def generate_data_quality_report(directory_data, kpi_data, docs_analysis):
    """Generate data quality observations"""
    report = []
    report.append("# Data Quality Report\n")
    report.append(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append("## Completeness Check\n")

    # Check directory data
    report.append("### Employee Directory")
    complete_fields = ['name', 'email', 'team', 'role', 'timezone']
    missing_data = defaultdict(int)
    for person in directory_data:
        for field in complete_fields:
            if not person.get(field):
                missing_data[field] += 1

    if missing_data:
        report.append("**Issues found:**")
        for field, count in missing_data.items():
            report.append(f"- {count} employees missing {field}")
    else:
        report.append("- All employee records have complete data")
    report.append("")

    # Check KPI data
    report.append("### KPI Catalog")
    kpi_fields = ['kpi_name', 'definition', 'owner_team', 'primary_source', 'last_updated']
    kpi_missing = defaultdict(int)
    for kpi in kpi_data:
        for field in kpi_fields:
            if not kpi.get(field):
                kpi_missing[field] += 1

    if kpi_missing:
        report.append("**Issues found:**")
        for field, count in kpi_missing.items():
            report.append(f"- {count} KPIs missing {field}")
    else:
        report.append("- All KPI records have complete data")
    report.append("")

    # Check documents
    report.append("### Documents")
    all_docs = []
    for category, docs in docs_analysis.items():
        all_docs.extend(docs)

    docs_missing_date = sum(1 for doc in all_docs if not doc['last_updated'])
    report.append(f"- {docs_missing_date}/{len(all_docs)} documents missing 'Last updated' date")
    report.append("")

    report.append("## Consistency Check\n")

    # Check team naming consistency
    report.append("### Team Names")
    teams_in_directory = set(p['team'] for p in directory_data)
    teams_in_kpis = set(k['owner_team'] for k in kpi_data)
    teams_only_in_kpis = teams_in_kpis - teams_in_directory

    if teams_only_in_kpis:
        report.append(f"**Warning:** Teams in KPI catalog but not in directory:")
        for team in teams_only_in_kpis:
            report.append(f"- {team}")
    else:
        report.append("- All KPI owner teams exist in employee directory")
    report.append("")

    report.append("## Summary\n")
    report.append(f"- **Directory Records:** {len(directory_data)} complete")
    report.append(f"- **KPI Records:** {len(kpi_data)} total")
    report.append(f"- **Documents:** {len(all_docs)} total")
    report.append(f"- **Overall Data Quality:** {'Good' if not (missing_data or kpi_missing or teams_only_in_kpis) else 'Needs Review'}\n")

    return '\n'.join(report)

def main():
    """Main analysis function"""
    print("Loading data...")
    directory_data = load_directory_data()
    kpi_data = load_kpi_catalog()
    docs_analysis = analyze_documents()

    print("Analyzing teams and ownership...")
    team_data = analyze_teams_and_ownership(directory_data, kpi_data)

    print("Analyzing KPIs...")
    kpi_analysis = analyze_kpis(kpi_data)

    print("Generating reports...")

    # Create output directory
    os.makedirs('outputs', exist_ok=True)

    # Generate all reports
    reports = {
        'overview.md': generate_overview_report(directory_data, kpi_data, docs_analysis),
        'team_analysis.md': generate_team_analysis(team_data),
        'kpi_analysis.md': generate_kpi_analysis(kpi_analysis),
        'document_metadata.md': generate_document_metadata_analysis(docs_analysis),
        'policy_compliance.md': generate_policy_compliance_report(docs_analysis, kpi_data),
        'data_quality.md': generate_data_quality_report(directory_data, kpi_data, docs_analysis)
    }

    for filename, content in reports.items():
        output_path = f'outputs/{filename}'
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Generated {output_path}")

    print(f"\n✓ Analysis complete! {len(reports)} reports saved to data_analysis/outputs/")

if __name__ == '__main__':
    main()