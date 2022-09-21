function diff(){
	echo "Run cdk diff"
	set -o pipefail
	cd iac && cdk diff 2>&1 | tee output.log
	exitCode=${?}
	set +o pipefail
	echo ::set-output name=status_code::${exitCode}
	output=$(cat output.log)

	commentStatus="Failed"
	if [ "${exitCode}" == "0" ]; then
		commentStatus="Success"
	elif [ "${exitCode}" != "0" ]; then
		echo "CDK diff has failed. See above console output for more details."
		exit 1
	fi

	if [ "$GITHUB_EVENT_NAME" == "pull_request" ]; then
		commentWrapper="#### \`cdk diff\` ${commentStatus}
<details><summary>Show Output</summary>

\`\`\`
${output}
\`\`\`

</details>

*Workflow: \`${GITHUB_WORKFLOW}\`*
"

		payload=$(echo "${commentWrapper}" | jq -R --slurp '{body: .}')
		commentsURL=$(cat ${GITHUB_EVENT_PATH} | jq -r .pull_request.comments_url)

		echo "${payload}" | curl -s -S -H "Authorization: token ${GITHUB_TOKEN}" --header "Content-Type: application/json" --data @- "${commentsURL}" > /dev/null
	fi
}

diff