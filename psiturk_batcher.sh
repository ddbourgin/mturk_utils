#!/bin/bash
set -e
#set -x
set -o nounset # aka set -u

# WHAT IS THIS
# -------------
# This will use the `psiturk -e` functionality to post batches of hits to
# mturk, with each hit having no more than 9 assignments so that requesters
# don't get hammered by the extra 20% commission (yeesh).
#
#
# USAGE
# ---------
# The script has to be run from the same directory where your project's
# config.txt is located.
#
# First, set the variables at the beginning of the script (see the SET THESE
# section)
#
# Then, run the script on its own to make sure things look right:
#     ./psiturk_batcher.sh
#
# and then say 'no' so that you can launch it in the background instead.
#
# When things look right, launch it with `nohup`, redirect everything to a log
# file of your choice, and give it a 'y' so that the confirmation prompt is
# accepted, like this:
#
#     (echo y | nohup ./psiturk_batcher.sh | ts) > mylog.log 2>&1 &
#
# the `ts` will prepend a timestamp to each entry in the logfile. It's part of
# the `moreutils` package.
#
# Note: I only tested this on Debian so things may explode in non-GNU
# environments.  Hopefully you can figure out how to tweak it.
#
# Don't forget to change your config.txt to `launch_in_sandbox_mode = false` so
# that this script creates live hits for you.
#
# Okay go get'em!

##############################
# SET THESE
##############################
TOTAL_ASSIGNMENTS=250
SPACING=5 # the time to sleep before posting a new batch. put it in seconds
HIT_REWARD='0.75'
HIT_DURATION='1.00'
MAX_ASSIGNMENTS_PER_HIT=9

# DONE_BY
# something that `date -d` can understand, then convert it to seconds.
# See <https://www.gnu.org/software/coreutils/manual/html_node/Relative-items-in-date-strings.html#Relative-items-in-date-strings> for formats

DONE_BY=$(gdate -d 1minute +%s)
##############################

TOTAL_TIME=$(( ${DONE_BY}-$(gdate +%s) ))

NUM_ROUNDS=$(( $TOTAL_TIME / $SPACING ))
ASSIGNMENTS_PER_ROUND=$(( $TOTAL_ASSIGNMENTS / $NUM_ROUNDS ))
TOTAL_ASSIGNMENTS_DONE_WITHOUT_MODULUS=$(( NUM_ROUNDS * ASSIGNMENTS_PER_ROUND ))
ASSIGNMENTS_REMAINDER_TO_DISTRIBUTE=$(( TOTAL_ASSIGNMENTS % TOTAL_ASSIGNMENTS_DONE_WITHOUT_MODULUS ))
PSITURK_EXECUTE_FORMAT="hit create %s $HIT_REWARD $HIT_DURATION"

# <http://stackoverflow.com/questions/3231804/in-bash-how-to-add-are-you-sure-y-n-to-any-command-or-alias>
function confirm {
    # call with a prompt string or use a default
    read -e -r -p "${1:-Are you sure? [y/N]} " response
    case $response in
        [yY][eE][sS]|[yY])
            true
            ;;
        *)
            false
            ;;
    esac
}

meta=$(printf "%s\n" \
    "Total time: $TOTAL_TIME seconds" \
    "Spacing: ${SPACING} seconds" \
    "Total assignments: ${TOTAL_ASSIGNMENTS}" \
    "Assignments per round (ignoring modulus): ${ASSIGNMENTS_PER_ROUND}" \
    "Assignments remainder to distribute: ${ASSIGNMENTS_REMAINDER_TO_DISTRIBUTE}"\
    "Number of rounds: ${NUM_ROUNDS}")
echo "$meta" # so it goes to the logs...
echo

confirm_message=$(printf "%s\n" "$meta" '' 'Continue? [y/N] ')

confirm "${confirm_message}" || { echo 'exited...'; exit 0; }
echo

for (( i=1; i<=NUM_ROUNDS; i++ )); do
    echo "# ROUND ${i} FIGHT"
    num_assignments_this_round=$ASSIGNMENTS_PER_ROUND
    if (( i <= ASSIGNMENTS_REMAINDER_TO_DISTRIBUTE )); then
        ((num_assignments_this_round++))
    fi
    num_hits_this_round=$(( num_assignments_this_round / MAX_ASSIGNMENTS_PER_HIT ))
    num_assignments_for_modulus_hit=$(( num_assignments_this_round % MAX_ASSIGNMENTS_PER_HIT))
    echo "TOTAL assignments for this round: $num_assignments_this_round"
    for (( j=1; j<=num_hits_this_round; j++ )); do
        echo "Creating a hit with ${MAX_ASSIGNMENTS_PER_HIT} assignments."
        psiturk_execute=$(printf "$PSITURK_EXECUTE_FORMAT" $MAX_ASSIGNMENTS_PER_HIT)
        psiturk -e "$psiturk_execute"
    done

    # do one more hit creation, with the modulus.
    if (( num_assignments_for_modulus_hit > 0 )); then
        echo "Creating a hit with ${num_assignments_for_modulus_hit} assignments."
        psiturk_execute=$(printf "$PSITURK_EXECUTE_FORMAT" $num_assignments_for_modulus_hit)
        psiturk -e "$psiturk_execute"
    fi
    echo

    echo "Sleeping for ${SPACING} seconds..."; sleep ${SPACING}
    echo
done
