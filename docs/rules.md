# Rules
GitHub Watchman uses rules to provide the search terms to query GitHub and Regex patterns to filter out true positives.

They are written in YAML, and follow this format:
```yaml
---
filename:
enabled: #[true|false]
meta:
  name:
  author:
  date:
  description: #what the search should find#
  severity: #rating out of 100#
scope: #what to search, any combination of the below#
- code
- commits
- issues
- repositories
test_cases:
  match_cases:
  - #test case that should match the regex#
  fail_cases:
  - #test case that should not match the regex#
strings:
- #search query to use in GitHub#
pattern: #Regex pattern to filter out false positives#
```

Rules are stored in the directory watchman/rules, so you can see examples there.

**Scope**
This is where GitHub should look:
- code
- commits
- issues
- repositories

You can search for any combination of these, with each on its own line

**Test cases**
These test cases are used to check that the regex pattern works. Each rule should have at least one match (pass) and one fail case.

If you want to return all results found by a query, enter the value `blank` for both cases.

## Creating your own rules
You can easily create your own rules for GitHub Watchman. The two most important parts are the search queries and the regex pattern.

### Search queries
These are stored as the entries in the 'strings' section of the rule, and are the search terms used to query GitHub to find results.

Multiple entries can be put under strings to find as many potential hits as you can. So if I wanted to find passwords, I might use both of these search terms:
`- password`
`- password is`

#### Search terminology
The GitHub API uses query string syntax for search queries. You can see the GitHub documentation [here](https://docs.github.com/en/free-pro-team@latest/rest/reference/search#constructing-a-search-query)

An example where search qualifiers are used:
`GitHub+Octocat+in:readme+user:defunkt`

The Search API returns a maximum of 1000 results, so your search queries should be as specific as possible to catch all true positives.

### Regex pattern
This pattern is used to filter results that are returned by the search query.

If you want to return all results found by a query, enter the value `''` for the pattern.
