OPEN_PRS_WITH_CONTEXT = """
query OpenPRsWithContext(
  $owner: String!
  $name: String!
  $first: Int!
  $after: String
) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      states: OPEN
      first: $first
      after: $after
      orderBy: { field: UPDATED_AT, direction: DESC }
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        title
        body
        url
        createdAt
        updatedAt
        author {
          login
        }
        headRefName
        mergeable
        additions
        deletions
        changedFiles
        labels(first: 10) {
          nodes {
            name
          }
        }
        closingIssuesReferences(first: 5) {
          nodes {
            number
            title
            body
            labels(first: 10) {
              nodes {
                name
              }
            }
          }
        }
      }
    }
  }
}
"""

PR_FILES = """
query PRFiles(
  $owner: String!
  $name: String!
  $number: Int!
  $first: Int!
  $after: String
) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      files(first: $first, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          path
          additions
          deletions
        }
      }
    }
  }
}
"""

AUTHOR_HISTORY = """
query AuthorHistory(
  $mergedQuery: String!
  $reviewsQuery: String!
  $revertsQuery: String!
) {
  merged: search(query: $mergedQuery, type: ISSUE, first: 100) {
    issueCount
    nodes {
      ... on PullRequest {
        number
        mergedAt
      }
    }
  }
  reviews: search(query: $reviewsQuery, type: ISSUE, first: 20) {
    nodes {
      ... on PullRequest {
        comments {
          totalCount
        }
        reviews {
          totalCount
        }
      }
    }
  }
  reverts: search(query: $revertsQuery, type: ISSUE, first: 50) {
    nodes {
      ... on PullRequest {
        body
        mergedAt
      }
    }
  }
}
"""
