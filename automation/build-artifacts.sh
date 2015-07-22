#!/bin/bash -e

SAME_RPM_NAME=(
    fabric
)

is_in() {
    what="${1?}"
    where=("${@:2}")
    for word in "${where[@]}"; do
        if [[ "$word" == "$what" ]]; then
            return 0
        fi
    done
    return 1
}


echo "######################################################################"
echo "#  Building artifacts"
echo "#"

shopt -s nullglob

# cleanup
rm -Rf \
    exported-artifacts \
    dist \
    build
mkdir exported-artifacts

# Custom hacks to get the correct spec file
# to add the dist, and the requirements
python setup.py bdist_rpm --spec-only

sed -i \
  -e 's/Release: \(.*\)/Release: \1%{?dist}/' \
  dist/fabric-ovirt.spec

for requirement in $(grep -v -e '^\s*# ' requirements.txt); do
    requirement="${requirement%%<*}"
    requirement="${requirement%%>*}"
    requirement="${requirement%%=*}"
    requirement="${requirement##*#}"
    if is_in "$requirement" "${SAME_RPM_NAME[@]}"; then
        sed \
            -i \
            -e "s/Url: \(.*\)/Url: \1\nRequires:$requirement/" \
            dist/fabric-ovirt.spec
    else
        sed \
            -i \
            -e "s/Url: \(.*\)/Url: \1\nRequires:python-$requirement/" \
            dist/fabric-ovirt.spec
    fi
done

for requirement in $(grep -v -e '^\s*#' build-requirements.txt); do
    requirement="${requirement%%<*}"
    requirement="${requirement%%>*}"
    requirement="${requirement%%=*}"
    sed -i \
        -e "s/Url: \(.*\)/Url: \1\nBuildRequires:python-$requirement/" \
        dist/fabric-ovirt.spec
done

# generate tarball
python setup.py sdist

# create rpms
rpmbuild \
    -ba \
    --define "_srcrpmdir $PWD/dist" \
    --define "_rpmdir $PWD/dist" \
    --define "_sourcedir $PWD/dist" \
    dist/fabric-ovirt.spec

for file in $(find dist -iregex ".*\.\(tar\.gz\|rpm\)$"); do
    echo "Archiving $file"
    mv "$file" exported-artifacts/
done

rm -rf rpmbuild

echo "#"
echo "#  Building artifacts OK"
echo "######################################################################"

echo "######################################################################"
echo "#  Installation tests"
echo "#"

if which yum-deprecated &>/dev/null; then
    yum-deprecated install exported-artifacts/*rpm
else
    yum install exported-artifacts/*rpm
fi
ofab -l
fab-ovirt -l
ovirt-fabric -l

echo "#"
echo "# Installation OK"
echo "######################################################################"
