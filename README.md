manageiq-vmdb
=========

The `manageiq-vmdb` role allows for users of ManageIQ to modify and/or change VMDB objects via an Ansible Playbook.
The role includes a module `manageiq_vmdb` which does all the heavy lifting needed to modify or change objects in the database.

Requirements
------------

ManageIQ has to be Gaprindashvili (G Release) or higher.

The example playbook makes use of the `manageiq_vmdb` module which is also included as part of this role.

If you have a requirement to include this Role in Ansible Tower or Embedded Ansible, simply add an empty `roles`
directory at the root of your playbook and include a `requirements.yml` file with the following contents inside
that directory:

```
---
- src: syncrou.manageiq-vmdb
```

Role Variables
--------------

Validate Certs:
    `manageiq_validate_certs` defaults to `True`.
    If set to `False` in the `manageiq_connection` dictionary
    then the lookup will allow self signed certificates
    to be used when using SSL REST API connection urls.

ManageIQ:
    `manageiq_connection` is a dictionary with a set of connection defaults in `defaults/main.yml`.
    Remember to use Ansible Vault for passwords.
    `automate_workspace` is the guid required to talk to the Automate Workspace.

```
    manageiq_connection:
        url: 'http://localhost:3000'
        username: 'admin'
        password: 'password'
        automate_workspace: '1234'
        manageiq_validate_certs: false
```

Dependencies
------------

None

Example Playbook
----------------

An example which provisions a VM to EC2. The playbook
links that vm to a service in the ManageIQ VMDB using the
`manageiq_vmdb` module.
The example shows two ways to pass
the VMDB object to the module, either via an href slug or
via a variable.

```
- name: Service Linking VM's to an existing service
  hosts: localhost
  connection: local
  gather_facts: False

  vars:
  - key: db
  - name: db-test-provision-1
  - instance_type: t2.nano
  - security_group: sg-sdf234
  - image: ami-234234lkj
  - region: us-east-1
  - subnet: subnet-adsf098
  - manageiq_connection:
      url: 'https://localhost.ssl:3000'
      username: 'admin'
      password: 'smartvm'
      manageiq_validate_certs: false

  roles:
  - syncrou.manageiq-vmdb

  tasks:
  - name: Get a vmdb object
    manageiq_vmdb:
      href: "services/80"
    register: vmdb_object

  - name: Create Ec2 Instance
    ec2:
      key_name: "{{ key }}"
      instance_tags: {Name: "{{ name }}"}
      group_id: "{{ security_group }}"
      instance_type: "{{ instance_type }}"
      region: "{{ region }}"
      image: "{{ image }}"
      wait: yes
      count: 1
      vpc_subnet_id: "{{ subnet }}"
      assign_public_ip: yes
    register: ec2

  - name: Service Linking via an href slug
    manageiq_vmdb:
      href: "href_slug::services/80"
      action: add_provider_vms
      data:
        uid_ems:
          - "{{ ec2.instances[0].id }}"
        provider:
          id: 24

  - name: Service Linking via an object
    manageiq_vmdb:
      vmdb: "{{ vmdb_object }}"
      action: add_provider_vms
      data:
        uid_ems:
          - "asdf234"
        provider:
          id: 24
```

License
-------

Apache
