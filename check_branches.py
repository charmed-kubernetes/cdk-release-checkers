#!/usr/bin/env python3

'''
Script to compare commits between the stable channels on the Git repos, vs.
what the latest charms in stable were actually built with.
'''

import json
import os
import shutil
import traceback
import yaml
from pprint import pprint
from subprocess import call, check_output
from urllib.request import Request, urlopen

channel = os.environ.get('CHANNEL', "stable")
branch = os.environ.get('BRANCH', 'stable')

index_root = 'https://raw.githubusercontent.com/charmed-kubernetes/layer-index/master'


def get_layer_repo(layer_url):
    layer_type, layer_name = layer_url.split(':')
    if layer_type == 'charm':
        return charm_repos[layer_name]
    else:
        index_url = index_root + '/%ss/%s.json' % (layer_type, layer_name)
        with urlopen(index_url) as f:
            layer_info = json.load(f)
        return layer_info['repo'].strip()


results = []

# Get CI charm info
print('Getting charm info from CI')
with urlopen('https://raw.githubusercontent.com/charmed-kubernetes/jenkins/master/jobs/includes/charm-support-matrix.inc') as f:
    charm_support_matrix = yaml.safe_load(f)

charms = [
    (name, data)
    for dict in charm_support_matrix
    for name, data in dict.items()
    if 'k8s' in data['tags']
]
pprint(charms)
charm_urls = ['~%s/%s' % (data['namespace'], name) for name, data in charms]
charm_repos = {name: 'https://github.com/' + data['downstream'] for name, data in charms}

# Check manifests
manifest_urls = [
    'https://api.jujucharms.com/v5/%s/archive/.build.manifest?channel=%s' % (charm_url, channel)
    for charm_url in charm_urls
]
observed_commits = {}
for manifest_url in manifest_urls:
    print('Checking ' + manifest_url)
    request = Request(manifest_url)
    request.add_header('Cache-Control', 'max-age=0')
    try:
        with urlopen(request) as f:
            manifest = yaml.safe_load(f)
        for layer in manifest['layers']:
            layer_url = layer['url']
            layer_rev = layer['rev']
            if ':' not in layer_url:
                layer_url = 'charm:' + layer_url
            observed_commits.setdefault(layer_url, set()).add(layer_rev)
    except Exception:
        traceback.print_exc()
        results.append('Failed to reach ' + manifest_url)
pprint(observed_commits)

# Map observed layers to repos
layer_repos = {}
for layer, commits in observed_commits.items():
    print('Finding repo for ' + layer)
    repo = get_layer_repo(layer)
    layer_repos[layer] = repo
pprint(layer_repos)

# Fetch repos
repo_commits = {}
for layer, repo in layer_repos.items():
    print('Checking latest commit in ' + repo)
    shutil.rmtree('repo', ignore_errors=True)
    cmd = [
        'git', 'clone', repo, 'repo',
        '--branch', branch,
        '--depth', '1',
        '--single-branch'
    ]
    exit_code = call(cmd)
    if exit_code != 0:
        print('WARNING: could not clone repo ' + repo)
        repo_commits[layer] = None
        continue
    commit = check_output(['git', 'log', '-1', '--format=%H'], cwd='repo').decode('UTF-8').strip()
    repo_commits[layer] = commit

pprint(repo_commits)

# Check for mismatches
print('---- RESULTS ----')
for layer, repo_commit in repo_commits.items():
    repo = layer_repos[layer]
    observed_layer_commits = observed_commits[layer]
    if len(observed_layer_commits) == 1:
        observed_commit = list(observed_layer_commits)[0]
        if observed_commit != repo_commit:
            clean = False
            results.append('%s: %s is %s, but charms used commit %s' % (
                repo, branch, repo_commit, observed_commit
            ))
    else:
        results.append('%s: charms used multiple commits: %s' % (
            repo,
            ', '.join(observed_layer_commits)
        ))

# Print results
if results:
    for line in results:
        print(line)
else:
    print('No issues found.')
