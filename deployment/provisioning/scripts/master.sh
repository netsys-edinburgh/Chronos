#!/bin/bash
#set -u
#set -x

# Ensure this script is run once
if [ -f /local/.master-ready ]; then
    exit 0
fi

# Redirect output to log file
exec >> /local/master.log
exec 2>&1

echo "Starting Kubernetes Master installation..."

# Set env variables & install K8s, containerd and dependencies
source /local/repository/scripts/common.sh

sudo kubeadm init --config=config/kubeadm-config.yaml

# allow sN to log in with shared key
# see http://docs.powderwireless.net/advanced-topics.html
geni-get key > ${HOME}/.ssh/id_rsa
chmod 600 ${HOME}/.ssh/id_rsa
ssh-keygen -y -f ${HOME}/.ssh/id_rsa > ${HOME}/.ssh/id_rsa.pub
grep -q -f ${HOME}/.ssh/id_rsa.pub ${HOME}/.ssh/authorized_keys || cat ${HOME}/.ssh/id_rsa.pub >> ${HOME}/.ssh/authorized_keys

# https://github.com/kubernetes/kubernetes/issues/44665
sudo cp /etc/kubernetes/admin.conf $KUBEHOME/
sudo chown ${username}:${usergid} $KUBEHOME/admin.conf

# Install Flannel. See https://github.com/coreos/flannel
sudo kubectl apply -f /local/repository/config/flannel-network-conf.yaml


# Allow scheduling of pods on master
kubectl taint node $(kubectl get nodes -o json | jq -r .items[0].metadata.name) node-role.kubernetes.io/master:NoSchedule-

# install helm
echo "Installing Helm"
wget https://get.helm.sh/helm-v3.1.0-linux-amd64.tar.gz
tar xf helm-v3.1.0-linux-amd64.tar.gz
sudo cp linux-amd64/helm /usr/local/bin/helm

# Wait till the slave nodes get joined and update the kubelet daemon successfully
# number of slaves + 1 master
node_cnt=$(($(/local/repository/scripts/geni-get-param.sh computeNodeCount) + 1))
# 1 node per line - header line
joined_cnt=$(( `kubectl get nodes | wc -l` - 1 ))
while [ $node_cnt -ne $joined_cnt ]
do 
    joined_cnt=$(( `kubectl get nodes | wc -l` - 1 ))
    echo "Total nodes: $node_cnt Joined: ${joined_cnt}"
    sleep 1
done
echo "All nodes joined"

#Deploy metrics server
sudo kubectl create -f config/metrics-server.yaml
sudo kubectl apply -f /local/repository/config/usrp.yaml
# to know how much time it takes to instantiate everything.
echo "Kubernetes Master Setup DONE!"
date

touch /local/.master-ready