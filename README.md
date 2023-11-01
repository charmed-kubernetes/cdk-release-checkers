DEPRECATED: These scripts were used to verify release commits and revisions of
reactive charms published to the old Charm Store. They are no longer used.

A couple scripts I've been using to verify commits and revisions in
Charmed Kubernetes releases. Long-term this functionality (not necessarily
these scripts) should land in https://github.com/charmed-kubernetes/jenkins.

# check_branches.py

Compares commits between the stable channels on the Git repos, vs.
what the latest charms in stable were actually built with.

This script also checks for differences between stable and master branches on
layers that the charms were built with. Note that differences here are expected
in bugfix releases, but the script will print them as warnings anyway.

```
CHANNEL=candidate BRANCH=stable ./check_branches.py
```

# verify-bundle-revs

Verifies that charm revisions in bundles match the charm revisions in the charm
store.

```
CHANNEL=canididate ./verify-bundle-revs
```
