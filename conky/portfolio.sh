#!/bin/bash

TMPFILE=/tmp/portfolio
PORTFOLIO_PATH=/home/andieh/src/portfolio




function fetch {
    cd $PORTFOLIO_PATH
    python2 portfolio.py -p > $TMPFILE
}

if [ -z $1 ]
then
    echo "please give me some input"
    exit 0
fi

if [ $1 == "fetch" ]
then
    fetch
else
    if [ ! -e $TMPFILE ]
    then
        fetch
    fi

    LINE=$(cat $TMPFILE | grep -A1 "\[$1\]" | grep -v $1)
    if [ "x$LINE" == "x" ]
    then
        echo "symbol not found" 
        exit 1
    fi

    if [ -z $2 ]
    then
        echo $LINE
        exit 0
    else
        ARR=$(echo $LINE | tr "," "\n")
        for X in $ARR
        do
            NAME=$(echo $X | awk -F':' '{print $1}')
            if [ $NAME == $2 ]
            then
                echo $(echo $X | awk -F':' '{print $2}')
                exit 0
            fi
        done
        echo "-1"
        exit 1
    fi
fi


