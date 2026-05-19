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
