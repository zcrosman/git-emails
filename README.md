# GitEmails

This Python script is designed to fetch GitHub repositories and commit emails for a specified user or organization, efficiently handling GitHub's rate limiting by utilizing multiple tokens. It's useful for Open Source Intelligence (OSINT) tasks, allowing for the collection of potentially valuable data about public repositories and their contributors.

## Features

- Fetch all repositories for a given GitHub user or organization.
- Extract commit emails from the repositories' commit history.
- Handle GitHub API rate limits by rotating through multiple tokens.
- Output the collected data into a CSV file for easy analysis.

## Usage

For a GitHub organization:
```bash
python gitemails.py --org <organization_name>
```

Authentication:
To avoid rate limits, you can use a personal access token:

```bash
python gitemails.py --user <username> --token <your_github_token>
```

Or, to rotate through multiple tokens:
    - The tokens file should contain one token per line.
```bash
python gitemails.py --user <username> --token-file <path_to_tokens_file>
```

## Output

The script generates a CSV file named github-data-<target>.csv with the following columns:

    Repo Name
    Repo URL
    Repo Owner
    Username
    Role (Owner or Contributor)
    Type (Commit Author or Commit Committer)
    Email
    Commit URL
    Commit API URL
