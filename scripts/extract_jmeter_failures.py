#!/usr/bin/env python3
"""Extract failures from a JMeter JTL (CSV or XML) and save response bodies as HTML files.

Usage: python scripts/extract_jmeter_failures.py <jtl-file> <out-dir>
Produces: out-dir/failure_<n>.html and out-dir/failures-summary.json
"""
import sys
import os
import json
from xml.etree import ElementTree as ET


def extract_from_csv(path, out_dir):
    try:
        import pandas as pd
    except Exception:
        print("ERROR: pandas is required to parse CSV JTL. Install with: pip install -r requirements.txt")
        raise
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    # try to find responseData or success
    resp_col = None
    for c in df.columns:
        if 'responsedata' in c or 'response_data' in c or 'response' == c:
            resp_col = c
            break

    success_col = None
    for c in df.columns:
        if c == 'success':
            success_col = c
            break

    failures = []
    for i, row in df.iterrows():
        is_fail = False
        if success_col:
            is_fail = str(row[success_col]).strip().lower() not in ('true', '1', 't')
        if resp_col and (is_fail or pd.notna(row[resp_col])):
            body = str(row[resp_col]) if pd.notna(row[resp_col]) else ''
            fname = os.path.join(out_dir, f'failure_{i+1}.html')
            with open(fname, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(body)
            failures.append({'index': int(i), 'file': fname})

    return failures


def extract_from_xml(path, out_dir):
    tree = ET.parse(path)
    root = tree.getroot()
    failures = []
    i = 0
    for elem in root:
        # sample elements may be httpSample or sample
        tag = elem.tag
        if 'sample' in tag.lower() or 'httpsample' in tag.lower():
            i += 1
            success = elem.get('s') or elem.get('success') or elem.get('success')
            # locate responseData child
            resp = None
            for child in elem:
                if child.tag.lower().endswith('responsedata') or child.tag.lower().endswith('response'):
                    resp = child.text
                    break
            is_fail = False
            if success is not None and success.lower() in ('false', '0'):
                is_fail = True
            if is_fail or (resp and resp.strip()):
                fname = os.path.join(out_dir, f'failure_{i}.html')
                with open(fname, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(resp or '')
                failures.append({'index': i, 'file': fname})

    return failures


def main():
    if len(sys.argv) < 3:
        print('Usage: extract_jmeter_failures.py <jtl-file> <out-dir>')
        sys.exit(1)

    path = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    failures = []
    try:
        if path.lower().endswith('.csv'):
            failures = extract_from_csv(path, out_dir)
        else:
            # try xml
            failures = extract_from_xml(path, out_dir)
    except Exception as e:
        print('Error extracting failures:', e)
        sys.exit(2)

    summary = {'source': path, 'count': len(failures), 'failures': failures}
    summary_path = os.path.join(out_dir, 'failures-summary.json')
    with open(summary_path, 'w') as s:
        json.dump(summary, s, indent=2)

    print('Extracted', len(failures), 'failures to', out_dir)


if __name__ == '__main__':
    main()
