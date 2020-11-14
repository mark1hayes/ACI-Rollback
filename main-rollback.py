import snapsub
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import sys
import time
import getpass
# Python 2 and 3 have different input functions - raw_input and input
try:
    import __builtin__
    input = getattr(__builtin__, 'raw_input')
except (ImportError, AttributeError):
    pass


def take_snapshot(apic, cookies, snapshot_name):
    query = snapsub.Query(apic, cookies)
    query_string = 'configSnapshot'
    query_payload = query.query_class(query_string)
    payload_len = len(query_payload[1]['imdata'])
    snap_count = 0
    for x in range(0, payload_len):
        if (query_payload[1]['imdata'][x]['configSnapshot']['attributes']
            ['fileName'])[4:17] == snapshot_name:
            snap_count += 1

    if snap_count > 0:
        print("A snapshot with that name ({}) already exists. Please change th"
              "e name of the snapshot, or delete the exist"
              "ing snapshot. Exiting.".format(snapshot_name))
        sys.exit()
    elif snap_count == 0:
        snapshot = 'true'
        status = 'created,modified'
        cfgmgmt = snapsub.FabCfgMgmt(apic, cookies)
        status = cfgmgmt.backup(snapshot_name, snapshot, status)
        if status == 200:
            print("")
            print("Snapshot '%s' taken successfully, you may proceed with Change Request." % (snapshot_name))
            time.sleep(5)
        else:
            print("")
            print("Snapshot failed for some reason.")
            del_snap_pol(apic, cookies, snapshot_name)
            sys.exit()


def revert_snapshot(apic, cookies, snapshot_name):
        query = snapsub.Query(apic, cookies)
        query_string = 'configSnapshot'
        query_payload = query.query_class(query_string)
        payload_len = len(query_payload[1]['imdata'])
        for x in range(0, payload_len):
            if (query_payload[1]['imdata'][x]['configSnapshot']['attributes']
                ['fileName'])[4:18] == snapshot_name:
                snapshot_name = (query_payload[1]['imdata'][x]
                                 ['configSnapshot']['attributes']
                                 ['fileName'])
                break
        cfgmgmt = snapsub.FabCfgMgmt(apic, cookies)
        cfgmgmt.snapback(snapshot_name)
        print("Rolled back to previous '%s' snapshot" % (snapshot_name))


def del_snap_pol(apic, cookies, snapshot_name):
    status = 'deleted'
    snapshot = 'true'
    cfgmgmt = snapsub.FabCfgMgmt(apic, cookies)
    status = cfgmgmt.backup(snapshot_name, snapshot, status)
    print "Config Export policy removed from ACI (Tidy up)"
    print "Please manually delete snapshot image from apic if you want to re-use '%s'" % (snapshot_name)

def collect_addr_cred(addr_cred_old):
    # If any of the address, username or password is empty, collect them interactively
    addr_cred_new = []
    if addr_cred_old[0] == "" or addr_cred_old[0] is None:
        print("\nAPIC IP address is not defined; please enter it at the prompt")
        # addr_cred_new.append(str(input("Address: ")))
        addr_cred_new.append(str(input("Address: ")))
    else:
        addr_cred_new.append(addr_cred_old[0])
    if addr_cred_old[1] == "" or addr_cred_old[1] is None:
        print("\nAPIC Username is not defined; please enter it at the prompt")
        # addr_cred_new.append(str(input("Username: ")))
        addr_cred_new.append(str(input("Username: ")))
    else:
        addr_cred_new.append(addr_cred_old[1])
    if addr_cred_old[2] == "" or addr_cred_old[2] is None:
        print("\nAPIC Password is not defined; please enter it at the prompt")
        addr_cred_new.append(str(getpass.getpass(prompt="Password: ")))
    else:
        addr_cred_new.append(addr_cred_old[2])
    return addr_cred_new

def main():
    # Disable urllib3 warnings
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    # Static APIC information
    apic = ""
    user = ""
    pword = ""
    # Verify that APIC address, username and password variables are not empty
    addr_cred_static = [apic, user, pword]
    addr_cred_checked = collect_addr_cred(addr_cred_static)
    apic = addr_cred_checked[0]
    user = addr_cred_checked[1]
    pword = addr_cred_checked[2]
	# get snapshot name and prepend '_pre' to it.
    while True:
	snapshot_input = input ("Please enter Change Reference (all 10 characters) or press return to use [RollBack01]: ") or "RollBack01"
	# check length
	if  not len(snapshot_input) == 10:
		print("Sorry, the filename must be 10 characters in length e.g. 'CHG1234567'")
		continue
	else:
		snapshot_name = "Pre_" + snapshot_input
		print snapshot_name + " will be used as the snapshot name on ACI."
		break
    # Initialize the fabric login method, passing appropriate variables
    print "Connecting to Fabric API"
    fablogin = snapsub.FabLogin(apic, user, pword)
    # Run the login and load the cookies var
    cookies = fablogin.login()
    # Take snapshot before deployment
    print "Attempting to take snapshot"
    take_snapshot(apic, cookies, snapshot_name)
    # Prompt to see if user wants to rollback to previous snapshot
    user_input = input("\nRollback 'y' or 'n' [n]: ")
    selection = user_input or 'n'
    # Run the login and load the cookies var
    cookies = fablogin.login()
    # Revert only if requested.
    if selection.lower() == 'y':
    	revert_snapshot(apic, cookies, snapshot_name)
    # Delete the snapshot policy
    del_snap_pol(apic, cookies, snapshot_name)
    # End
    print("Script End")


if __name__ == '__main__':
    main()
