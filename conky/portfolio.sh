#!/bin/bash

# the file where portfolio dumps its raw data
TMPFILE=/tmp/portfolio_dump.csv

# python executable 
PYEXE=python2


function fetch {
    cd $portfolio_path
    $PYEXE $portfolio_path/portfolio.py -p > $TMPFILE
}

function usage {
    echo "Usage: `basename $0` [-h] [-d] [-p path_to_portfolio] [-f] [-c <cache mins to life>] <symbol name> <field>>|'fetch'"
}


# force new data fetch
force=0
# action, either fetch or specific symbol
action=""
# field to extract from symbol in action 
field=""
# cachefile time to life 
ttl_cache=15
# portfolio source directory
portfolio_path=
# debug switch 
debug=0


# no arg passed, complain!
if (($# == 0)); then
  echo "[ERR] no arguments provided" >&2
  echo
  usage
  exit 1
fi

# option parsing (first force reset getopts)
OPTIND=1
while getopts ":p:dhfc:" opt; do
    case "$opt" in
      h)  usage 
	  exit 0 
	  ;;
      f)  force=1
	  ;;
      p)  portfolio_path=${PORTFOLIO_PATH:=$OPTARG} 
	  ;;
      c)  ttl_cache=$OPTARG 
	  ;;
      d)  debug=1
	  ;;
    esac
done
# shift to leftover args 
shift $((OPTIND-1))
# reset afterwards, too
OPTIND=1

# check for correct positional arguments
if [ -z "$2" ] && [[ "$1" != "fetch" ]]; then 
    echo "[ERR] Please provide either 'fetch' to fetch data only," >&2
    echo "[ERR] or <symbol> <field> to extract <field> from <symbol>" >&2
    echo 
    usage 
    exit 1
elif [[ "$1" = "fetch" ]]; then 
    action="fetch"
else 
    action=$1
    field=$2
fi

# some debug output
if [[ "$debug" = "1" ]]; then 
    echo "Showing internal variables:" 
    echo "force: $force"
    echo "action: $action"
    echo "field: $field"
    echo "path: $portfolio_path"
    echo "cache ttl: $ttl_cache"
    echo "debug: $debug"
fi

# make sure we have a portfolio path
if [[ "$portfolio_path" = "" ]]; then 
    echo "[ERR] No portfolio path provided, either set the env var: PORTFOLIO_PATH," >&2
    echo "      or provide a path as argument using the -p option" >&2
    echo
    usage 
    exit 1
fi

# check if TTL for portfolio dumpfile is reached
find `dirname $TMPFILE` -name `basename $TMPFILE` -type f -mmin +${ttl_cache} -delete

# fetch cachefile, if needed
([ ! -e $TMPFILE ] || [[ "$force" = "1" ]]) && fetch

# exit gracefully, if action==fetch
if [[ "$action" = "fetch" ]]; then 
    exit 0
fi

# parse dump file - grep correct line 
data=`grep -A 1 "\[${action}\]" $TMPFILE | tail -n 1`

# more debug
if [[ "$debug" = "1" ]]; then 
    echo "dataline: $data "
fi

# verify that line was extracted
if [[ "$data" = "" ]]; then 
    echo "[ERR] Could not parse $TMPFILE" >&2
    echo "[ERR] Maybe try -f to force new fetch" >&2
    echo "[ERR] Make sure your <symbol> exists" >&2
    usage
    exit 1
fi

# extract field from data-line
for d in `echo $data | tr "," "\n"`
do
    name=$(echo $d | awk -F':' '{print $1}')
    if [[ "$name" = "$field" ]]; then
	# output field value
	echo $(echo $d | awk -F':' '{print $2}')
	exit 0
    fi
done
