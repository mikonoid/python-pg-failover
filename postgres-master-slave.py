#!/usr/bin/python3
 
#############
import subprocess, paramiko, sys, time, smtplib, os, re, socket, time
############
 
server = {
 'APP_MASTER1':
 { "hostname": "DS4193",
   "int_ip": "192.168.1.1",
   "ext_ip": "xxxxxxxx"},
 
 'APP_MASTER2':
 { "hostname": "DS4438",
   "int_ip": "192.168.1.4",
   "ext_ip": "xxxxxxxxxx"},
 
 'DB_MASTER':
 { "hostname": "DS4436",
   "int_ip": "192.168.1.2",
   "ext_ip": "xxxxxxxxx"},
 
 'DB_SLAVE':
 { "hostname": "DS4269",
   "int_ip": "192.168.1.3",
   "ext_ip": "xxxxxxxxxxx"}
}
 
logfile = "/root/monscripts/log/error.log"
mail_server = "localhost"
mail_from = "root@xxxxxxx"
mail_to = ["notify@xxxxxxxxx", "mikonoid@gmail.com"]
hostname = socket.gethostname()
 
###########
def log_write(log):
    fd = open(logfile, 'a')
    log = str(time.strftime("%Y/%m/%d %H:%M:%S | ")) + str(sys.argv[0]) + " | " + log + "\n"
    fd.write(log)
 
###
def mail_send(mail_body):
    mail_subj =  str(time.strftime("%Y/%m/%d %H:%M:%S ")) + str(sys.argv[0]) + " Notification from " + hostname
    message = """\
From: %s
To: %s
Subject: %s \n
%s
-------------
Contact Vizl or mk.ivanov (skype).
See more details in %s on the %s
""" % (mail_from, ', '.join(mail_to), mail_subj, mail_body, logfile, hostname)
    server = smtplib.SMTP(mail_server)
    server.sendmail(mail_from, mail_to, message)
    server.quit()
 
###
def notify(log, to_Log, to_Email):
    if to_Log == True:
        log_write(log)
    if to_Email == True:
        mail_send(log)
 
###
def ping_check(host):
    ping = subprocess.Popen(["/usr/bin/fping", "-t 200",  host], stdout=subprocess.PIPE)
    result = str(ping.stdout.read())
    re_unreach = re.compile(host + " is unreachable")
    if re_unreach.findall(result):
        return False
    else:
        return True
 
###
def run_remote_ssh(command, host):
    key = paramiko.RSAKey.from_private_key_file("/root/.ssh/id_rsa")
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.load_system_host_keys()
    s.connect(host, 222, pkey=key, timeout=10)
    stdin, stdout, stderr = s.exec_command(command)
    return stderr.readlines(), stdout.readlines()
 
###
def run_remote_command(command, host):
    hostname = host["hostname"]
    ip = host["int_ip"]
    ssh_stderr, ssh_stdout = run_remote_ssh(command, ip)
    start_mess = "Running command '" + command + "' on the " + hostname + " " + ip
    notify(start_mess, 1, 0)
    if len(ssh_stderr) == True:
        output = ' '.join(ssh_stderr)
        err_mess = "Error when running '" + command + "' on the " + hostname + " " + ip + "\n" + output
        notify(err_mess, 1, 1)        
    else:
        output = ' '.join(ssh_stdout)
        notify(output, 1, 0)
 
###
def change_master_slave(curr_master, new_master, app_node):
    trigger_file = "/usr/local/pgsql/data/replica.trigger"
    run_remote_command('touch ' + trigger_file, new_master)
    run_remote_command('route del 192.168.1.100 ' + curr_master['int_ip'], app_node)
    run_remote_command('route add 192.168.1.100 ' + new_master['int_ip'], app_node)
    mess = "Postgresql Master was changed on " + app_node['hostname'] + ' from ' + \
           curr_master["hostname"] + ' to ' + new_master["hostname"]
    notify(mess, 1, 1)
 
###########
while True:
    time.sleep(10)
    if (ping_check(server['DB_MASTER']['int_ip']) or ping_check(server['DB_MASTER']['ext_ip'])) is False:
        if ping_check('8.8.8.8') is True:
            time.sleep(10)
            if ping_check(server['DB_MASTER']['int_ip']) is False:
                mess = server['DB_MASTER']['hostname'] + ' is down. Switch DB traff to slave ' + \
                       server['DB_SLAVE']['hostname']
                notify(mess, 1, 1)
                change_master_slave(server['DB_MASTER'], server['DB_SLAVE'], server['APP_MASTER1'])
                change_master_slave(server['DB_MASTER'], server['DB_SLAVE'], server['APP_MASTER2'])
                break
        else:
            mess = "DB MASTER " + server['DB_MASTER']['hostname'] + " and global inet 8.8.8.8 is down"
            notify(mess, 1, 1)
    elif ping_check(server['DB_MASTER']['int_ip']) is False:
         mess = "Cant ping internal IP of DB_MASTER " + server['DB_MASTER']['int_ip'] + \
                " on the " +  server['DB_MASTER']['hostname'] + " Check internal network only."
         notify(mess, 1, 1)
    elif ping_check(server['DB_MASTER']['ext_ip']) is False:
         mess = "Cant ping external IP of DB_MASTER " + server['DB_MASTER']['ext_ip'] + \
                " on the " + server['DB_MASTER']['hostname'] + " Check external network only."
         notify(mess, 1, 1)
    elif ping_check('8.8.8.8') is False:
         mess = "Global Inet is down. Can't ping 8.8.8.8"
         notify(mess, 1, 0)
    else:
         pass
