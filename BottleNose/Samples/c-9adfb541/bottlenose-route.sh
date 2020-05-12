#!/bin/bash
let "a = 0"
routeTableFix="false"
ipTableFix="false"
curlFix="false"

routeOutput="$(route -n | grep 172.31.0.3)"
if [ "$routeOutput" == "" ]; then
let "a += 1"
routeTableFix="true"
fi

iptableOutputhttp="$(iptables -L | grep -w http)"
if [ "$iptableOutputhttp" == "" ]; then
let "a += 1"
ipTableFix="true"
fi

curlOutput="$(curl -s 172.31.0.20 --connect-time 1 --max-time 1)"
if [ "$curlOutput" == "congrats you have been successful in reaching me" ]; then
let "a += 1"
curlFix="true"
fi

if [ $a -eq 0 ]
then
echo "Sorry! You have not completed the lab. Please follow the steps mentioned in wiki to finish the lab:$routeTableFix:$ipTableFix:$curlFix"
elif [ $a -eq 1 ]
then
echo "You have completed 33 percent of the Lab correctly:$routeTableFix:$ipTableFix:$curlFix"
elif [ $a -eq 2 ]
then
echo "You have completed 66 percent of the Lab correctly:$routeTableFix:$ipTableFix:$curlFix"
elif [ $a -eq 3 ]
then
echo "You have completed the lab successfully:$routeTableFix:$ipTableFix:$curlFix"
else
echo "Sorry! You have not completed the lab. Please follow the steps mentioned in wiki to finish the lab:$routeTableFix:$ipTableFix:$curlFix"
fi