#!/usr/bin/env groovy

// Note:
// Activating the virtualenv doesn't stay active across
// sh invocations in pipeline scripts.
// See https://issues.jenkins-ci.org/browse/JENKINS-37116

node {
  try {

    slackNotify("STARTED")

    // Stamp exact states of repos and run unit tests
    stage('Unit Tests') {
      sh 'rm -rf repo-state.txt venv'
      checkout scm
      sh "spynl/cli/ops/prepare-stage.sh -u $scm_urls -r $revision -f $fallbackrevision -m && spynl/cli/ops/run-unit-tests.sh"
      archive 'repo-state.txt'                              // for history
      stash name:'repo-state', includes:'**/repo-state.txt' // for using it again later in this build
      junit 'venv/**/pytests.xml'
      //coverage 'venv/**/coverage.xml'  // Check this ticket: https://issues.jenkins-ci.org/browse/JENKINS-30700
    }

    // Build Docker Image and deploy to dev or production ECR
    stage('Deploy') {
      checkout scm
      unstash name:'repo-state'
      sh "spynl/cli/ops/prepare-stage.sh -u $scm_urls -r $revision -f $fallbackrevision"
      sh "source venv/bin/activate && spynl ops.deploy --buildnr ${env.BUILD_NUMBER} --task $task"
      archive 'spynl/cli/ops/docker/docker.build.log'  // for debugging
    }

    // Run smoke test to see if Spynl actually arrived
    stage('Smoke Tests') {
      if (task != "production" ){
        sleep time:90, unit:'SECONDS'
        checkout scm
        sh "source venv/bin/activate && spynl ops.smoke_test --task $task"
      }
    }

  } catch (e) {
    currentBuild.result = "FAILED"
    throw e
  } finally {
   // Success or failure, always send notifications
   slackNotify(currentBuild.result)
  }
}


// Send Slack Notifications
def slackNotify(String buildStatus = 'STARTED') {
  buildStatus =  buildStatus ?: 'SUCCESSFUL'

  def colorCode = '#e60000'

  if (buildStatus == 'STARTED') {
    colorCode = '#ff8c00'
  } else if (buildStatus == 'SUCCESSFUL') {
    colorCode = '#32cd32'
  } else {
    colorCode = '#e60000'
  }

  slackSend (color: "${colorCode}", message: "${buildStatus}: Job ${env.JOB_NAME.replaceAll('%2F', '/')} Build ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)")
}
