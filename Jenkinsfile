#!/usr/bin/env groovy

node {
  try {

    slackNotify("STARTED")

    // Stamp exact states of repos and run unit tests
    stage('Unit Tests') {
      sh 'rm -rf repostate.txt venv'
      sh "${workspace}/cli/ops/run-unit-tests.sh $repos $revision $fallbackrevision $spynlrevision $configrepo"
      archive 'repostate.txt'                                // for history
      stash name:'repostate', includes:'**/repostate.txt'    // for using it again later in this build
      junit 'venv/**/pytests.xml'
      //coverage 'venv/**/coverage.xml'  // Check this ticket: https://issues.jenkins-ci.org/browse/JENKINS-30700
    }

    // Deploy to swcloud or softwearconnect depending on the REVISION
    stage('Deploy') {
      unstash name:'repostate'
      sh "${workspace}/cli/ops/prepare-stage.sh $repos $revision $fallbackrevision $spynlrevision $configrepo"
      sh "source venv/bin/activate && spynl ops.deploy --buildnr ${env.BUILD_NUMBER} --config-repo $configrepo --task $task --revision $revision --fallbackrevision $fallbackrevision"
      archive 'venv/src/spynl/cli/ops/docker/docker.build.log'  // for debugging
    }

    // Run smoke test to see if Spynl actually arrived
    stage('Smoke Tests') {
      if (task != "production" ){
        sleep time:90, unit:'SECONDS'
        sh "${workspace}/cli/ops/prepare-stage.sh $repos $revision $fallbackrevision $spynlrevision $configrepo"
        sh "source venv/bin/activate && spynl ops.smoke_test --repos $repos --config-repo $configrepo --task $task"
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
