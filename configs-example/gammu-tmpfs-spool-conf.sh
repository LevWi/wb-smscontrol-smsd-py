mount -t tmpfs -o size=20M tmpfs /mnt/tmpfs-spool/
mkdir /mnt/tmpfs-spool/gammu
mkdir /mnt/tmpfs-spool/gammu/inbox
mkdir /mnt/tmpfs-spool/gammu/outbox
mkdir /mnt/tmpfs-spool/gammu/sent
mkdir /mnt/tmpfs-spool/gammu/error


/usr/bin/wb-gsm restart_if_broken &

/usr/bin/python /home/wb_mainWorker.py &

service gammu-smsd start

