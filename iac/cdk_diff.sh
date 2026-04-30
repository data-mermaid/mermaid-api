function diff(){
	echo "Run cdk diff"
	set -o pipefail
	cdk diff 2>&1 | tee /tmp/cdk-diff.log
	exitCode=${?}
	set +o pipefail

	if [ "${exitCode}" != "0" ]; then
		echo "CDK diff has failed. See above console output for more details."
		exit 1
	fi
}

diff