#!/bin/bash

set -e

SELF="$0"

usage() {
    (echo "$SELF dir dns-name -- generate root and end-entity certificates for the pubsub into dir for host dns-name"
     echo "use localhost as dns-name for testing, or set checkHostnames to False in test scripts") > /dev/stderr
    exit 0
}

[ -z "$1" ] && usage
[ -z "$2" ] && usage

DIR="$1"
DNSNAME="$2"
RSABITS=4096

mkdir -p "$DIR"
cd "$DIR"

## (1) Generate ROOT CA certificate
openssl genrsa -out root.key 4096
# write CA configuration file
cat >root-conf <<EOF
[ req ]
default_bits = $RSABITS
default_key=root.key
distinguished_name = my_req_distinguished_name
encrypt_key = no
utf8 = yes
req_extensions = my_extensions
prompt = no

[ my_req_distinguished_name ]
C = DE
ST = Saxony
L = Dresden
O  = SELIS
CN = selisproject.eu

[ my_extensions ]
basicConstraints=critical,CA:TRUE
subjectAltName=@my_subject_alt_names
subjectKeyIdentifier = hash
keyUsage=critical, keyCertSign

[ my_subject_alt_names ]
DNS.1 = selisproject.eu
EOF
# generate certificate
openssl req -new -x509 -key root.key -sha256 -config root-conf -extensions my_extensions -out root.crt -days 1095
# now, the Root private key is in "root.key", Root certificate is in "root.crt"


## (2) Generate PubSub TLS certificate
openssl genrsa -out pubsub.key 4096
# write pubsub end-entity configuration file
cat >pubsub-conf <<EOF
[ req ]
default_bits = $RSABITS
default_key=pubsub.key
distinguished_name = my_req_distinguished_name
encrypt_key = no
utf8 = yes
req_extensions = my_extensions
prompt = no

[ my_req_distinguished_name ]
C = DE
ST = Saxony
L = Dresden
O  = SELIS
CN = $DNSNAME

[ my_extensions ]
basicConstraints=critical,CA:FALSE
subjectAltName=@my_subject_alt_names
subjectKeyIdentifier = hash
#authorityKeyIdentifier  = keyid:always, issuer:always
keyUsage=critical, nonRepudiation, digitalSignature, keyEncipherment, keyAgreement
extendedKeyUsage = critical, serverAuth

[ my_subject_alt_names ]
DNS.1 = $DNSNAME
DNS.2 = localhost
EOF

# generate private key of the pubsub server
openssl req -new -key pubsub.key -out pubsub.csr -config pubsub-conf


## (3) Sign the certificate with root CA
openssl x509 -req -in pubsub.csr -CA root.crt -CAkey root.key -CAcreateserial -out pubsub.crt -extfile pubsub-conf -extensions my_extensions -days 365
