<% commits.forEach(function (commit) { %>
[View Commit|https://github.com/SoftwearDevelopment/spynl/commit/<%= commit.sha1 %>] *<%= commit.title %>*\\
<%= commit.messageLines.join("\n    ") %>\\
<%= commit.authorName %> - <%= commit.committerDate %>

----
<% }) %>
