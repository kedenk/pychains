
# $1 for random seed
# $2 for amount of inputs

if [ -z ${1+x} ]; 
then 
    echo "No random seed is given as first parameter"; 
    exit 1;
fi
if [ -z ${2+x} ]; 
then 
    echo "No amount for input generation is given as second parameter"; 
    exit 1;
fi

INPUT_DIR=$3

if [ -z ${3+x} ]; 
then 
    INPUT_DIR=/home/user/ethereum/inputs
fi

RANDOM_SEED=$1
INPUT_AMOUT=$2

mkdir -p $INPUT_DIR

docker run -it -v $INPUT_DIR:/app/pychains/inputs -u `id -u $USER` pychains $RANDOM_SEED $INPUT_AMOUT
