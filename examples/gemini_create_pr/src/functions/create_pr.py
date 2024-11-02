from grpc import Status
from restack_ai.function import function
from src.functions.generate_pr_info import PrInfo
from dataclasses import dataclass
from git import Repo
import os
import re
import requests

@dataclass
class FunctionInputParams:
    repo_path: str
    pr_info: PrInfo

@function.defn(name="CreatePr")
async def create_pr(input: FunctionInputParams):
    """
    Create a PR for the given repository path
    """
    repo = Repo(input.repo_path)

    try:
        if repo.is_dirty():
            remote_url = repo.remotes.origin.url
            repo_match = re.search(r'github\.com[:/](.*?)(?:\.git)?$', remote_url)

            if not repo_match:
                raise ValueError("Could not parse repository name from remote URL")

            repo_name = repo_match.group(1)
            print(f"Detected repository: {repo_name}")
            print(remote_url)

            repo.git.checkout('HEAD', b=input.pr_info.branch_name)

            repo.git.add(A=True)

            repo.index.commit(input.pr_info.commit_message)

            origin = repo.remote(name="origin")
            origin.push(refspec=f"{input.pr_info.branch_name}:{input.pr_info.branch_name}")

            github_token = os.environ.get("GITHUB_TOKEN")

            headers = {"Authorization": f"token {github_token}"}
            data = {
                "title": input.pr_info.pr_title,
                "body": "This PR was generated by Gemini using the Restack AI Python SDK",
                "head": input.pr_info.branch_name,
                "base": "main"
            }
            response = requests.post(
                f"https://api.github.com/repos/{repo_name}/pulls",
                headers=headers,
                json=data
            )

            if response.status_code == 201:
                pr_url = response.json()['html_url']
                print(f"PR created: {pr_url}")
                return {"pr_url": pr_url, "status": "success"}
            else:
                print(f"Failed to create PR: {response.json()}")
        else:
            print("No changes to commit")
            return None
    except Exception as e:
        print(e)
        return None