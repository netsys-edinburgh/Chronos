#!/bin/bash
#set -u
#set -x

# Ensure this script is run once
if [ -f /local/.slave-ready ]; then
    exit 0
fi

echo "Starting Kubernetes Slave installation..."

# Set env variables & install K8s, containerd and dependencies
source /local/repository/scripts/common.sh

# use geni-get for shared rsa key
# see http://docs.powderwireless.net/advanced-topics.html
geni-get key > ${HOME}/.ssh/id_rsa
chmod 600 ${HOME}/.ssh/id_rsa
ssh-keygen -y -f ${HOME}/.ssh/id_rsa > ${HOME}/.ssh/id_rsa.pub

master_token=''
while [ -z $master_token ] 
do
    master_token=`ssh -o StrictHostKeyChecking=no master "export KUBECONFIG='/local/repository/kube/admin.conf' && kubeadm token list | grep authentication | cut -d' ' -f 1"`;
    sleep 1;
done
sudo kubeadm join master:6443 --token $master_token --discovery-token-unsafe-skip-ca-verification 

# patch the kubelet to force --resolv-conf=''
# sudo sed -i 's#Environment="KUBELET_CONFIG_ARGS=--config=/var/lib/kubelet/config.yaml"#Environment="KUBELET_CONFIG_ARGS=--config=/var/lib/kubelet/config.yaml --resolv-conf=''"#g' /etc/systemd/system/kubelet.service.d/10-kubeadm.conf
# sudo systemctl daemon-reload 
# sudo systemctl restart kubelet.service

# install a crontab to permanently save all Nervion logs
#crontab -l | { cat; echo "* * * * * /local/repository/config/test/savelogs.py"; } | crontab -

# if it complains that "[ERROR Port-10250]: Port 10250 is in use", kill the process.
# if it complains some file already exist, remove those. [ERROR FileAvailable--etc-kubernetes-pki-ca.crt]: /etc/kubernetes/pki/ca.crt already exists
sudo kubectl apply -f /local/repository/config/usrp.yaml

echo "Kubernetes Slave Setup DONE!"
date

touch /local/.slave-ready