FROM ubuntu:18.04
# contains already python 3.6

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-get install -y pandoc && \
    apt-get install -y python3-pip &&\
    apt-get -y clean &&\
    pip3 install pudb
#RUN apt-get install -y pandoc
#RUN apt-get update && \
#    apt-get install -y python3-pip && \
#    apt-get -y clean

WORKDIR /app

# pychains
ADD . /app/pychains/

#RUN pip3 install pudb

ENV PYTHONPATH /app/pychains/src/taintedstr:\
/app/pychains/src/tainteddatatypes:\
/app/pychains/src/python-performance-measurement:\
/app/pychains/subjects/py-evm-simulator/src/py-evm

WORKDIR /app/pychains/subjects/py-evm-simulator/src/py-evm
RUN ["python3", "setup.py", "install"]


WORKDIR /app/pychains 
#CMD ["/bin/bash"]
# execute pychains
#CMD ["./bin/100.bytecodevm.sh"]
ENTRYPOINT ["./bin/100.bytecodevm.sh"]

