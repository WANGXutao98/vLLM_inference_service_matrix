#!/bin/bash
source const.sh
chmod a-x check_all.sh

echo "stoping ${PROC} ...!"
PIDS=`ps -ef | grep ${PROC} | grep -v grep | awk '{print $2}'`

KILL=0
for PID in $PIDS
do
    kill -9 $PID
    KILL=1
done

if [ $KILL = 1 ] 
then
    echo "stop ${PROC} ok!"
else
    echo "Nothing stop!"
fi
