#!/usr/bin/env bash
TESTDIR=$1

cd $TESTDIR
for test in *.tests; do
    bash $test
done

