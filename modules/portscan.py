import os, glob, socket, time, json
from core import execute
from core import utils

from libnmap.parser import NmapParser
from libnmap.reportjson import ReportDecoder, ReportEncoder

class PortScan(object):
    """docstring for PortScan"""
    def __init__(self, options):
        utils.print_banner("Services Scanning")
        utils.make_directory(options['env']['WORKSPACE'] + '/portscan')
        self.module_name = self.__class__.__name__
        self.options = options

        # while not utils.checking_done(module='SubdomainScanning'):
        #     utils.print_info('Waiting SubdomainScanning module')
        #     time.sleep(100)
        self.initial()
        



    def initial(self):
        self.create_ip_result()
        self.masscan()


    #just for the masscan
    def create_ip_result(self):
        utils.print_good('Create IP for list of domain result')
        cmd = '$PLUGINS_PATH/massdns/bin/massdns -r $PLUGINS_PATH/massdns/lists/resolvers.txt -t A -o S -w $WORKSPACE/subdomain/massdns-IP-$OUTPUT.txt $WORKSPACE/subdomain/final-$OUTPUT.txt'

        cmd = utils.replace_argument(self.options, cmd)
        output_path = utils.replace_argument(self.options, '$WORKSPACE/subdomain/massdns-IP-$OUTPUT.txt')
        std_path = utils.replace_argument(self.options, '$WORKSPACE/subdomain/std-massdns-IP-$OUTPUT.std')
        execute.send_cmd(cmd, output_path, std_path, self.module_name)

        #matching IP with subdomain
        main_json = utils.reading_json(utils.replace_argument(self.options, '$WORKSPACE/$COMPANY.json'))
        with open(output_path, 'r') as i:
            data = i.read().splitlines()

        ips = []
        for line in data:
            if ' A ' in line:
                subdomain = line.split('. A ')[0]
                ip = line.split('. A ')[1]
                ips.append(ips)
                for i in range(len(main_json['Subdomains'])):
                    if subdomain == main_json['Subdomains'][i]['domain']:
                        main_json['Subdomains'][i]['IP'] = ip

        final_ip = utils.replace_argument(self.options, '$WORKSPACE/subdomain/final-IP-$OUTPUT.txt')

        with open(final_ip, 'w+') as fip:
            fip.write("\n".join(str(ip) for ip in ips))

        utils.just_write(utils.reading_json(utils.replace_argument(self.options, '$WORKSPACE/$COMPANY.json')), main_json, is_json=True)


    def masscan(self):
        utils.print_good('Starting masscan')

        main_json = utils.reading_json(utils.replace_argument(self.options, '$WORKSPACE/$COMPANY.json'))
        main_json['Modules'][self.module_name] = []

        if self.options['speed'] == 'slow':
            ip_list = [x.get("IP") for x in main_json['Subdomains']] + main_json['IP Space']

        elif self.options['speed'] == 'quick':
            ip_list = [x.get("IP") for x in main_json['Subdomains']]

        #Scan every 5 IP at time Increse if you want
        for part in list(utils.chunks(ip_list, 5)):
            for ip in part:
                cmd = 'sudo masscan --rate 10000 -p0-65535 {0} -oG $WORKSPACE/portscan/{0}-masscan.gnmap -oX $WORKSPACE/portscan/{0}-masscan.xml --wait 0'.format(ip)

                cmd = utils.replace_argument(self.options, cmd)
                output_path = utils.replace_argument(self.options, '$WORKSPACE/portscan/{0}-masscan.gnmap'.format(ip))
                std_path = utils.replace_argument(self.options, '$WORKSPACE/portscan/std-{0}-masscan.gnmap.std'.format(ip))
                execute.send_cmd(cmd, output_path, std_path, self.module_name)

            # check if previous task done or not every 30 second
            while not utils.checking_done(module=self.module_name):
                time.sleep(20)

            # update main json
            main_json['Modules'][self.module_name] += utils.checking_done(module=self.module_name, get_json=True)


    def result_parsing(self):
        utils.print_good('Parsing XML for masscan report')
        utils.make_directory(
            self.options['env']['WORKSPACE'] + '/portscan/parsed')
        result_path = utils.replace_argument(
            self.options, '$WORKSPACE/portscan')

        main_json = utils.reading_json(utils.replace_argument(
            self.options, '$WORKSPACE/$COMPANY.json'))

        for filename in glob.iglob(result_path + '/**/*.xml'):
            ip = filename.split('/')[-1].split('-masscan.xml')[0]
            masscan_report = NmapParser.parse_fromfile(filename)
            masscan_report_json = json.dumps(masscan_report, cls=ReportEncoder)

            #store the raw json
            utils.just_write(utils.replace_argument(
                self.options, '$WORKSPACE/portscan/parsed/{0}.json'.format(ip)), masscan_report_json, is_json=True)

            services = [x['__NmapHost__']['_services']
                     for x in masscan_report_json['_host']]
            ports = [y.get('_portid') for y in services]
            
            # open with()

            # ip = file.split('/')[-1].split('-masscan.xml')[0]


    def create_html(self):
        utils.print_good('Create beautify HTML report')

        utils.make_directory(self.options['env']['WORKSPACE'] + '/portscan/html-report')
        result_path = utils.replace_argument(self.options,'$WORKSPACE/portscan')


        for file in glob.iglob(result_path + '/**/*.xml'):
            ip = file.split('/')[-1].split('-masscan.xml')[0]

            cmd = 'xsltproc -o $WORKSPACE/portscan/html-report/{0}-html.html $PLUGINS_PATH/nmap-bootstrap.xsl {1}'.format(ip, file)

            cmd = utils.replace_argument(self.options, cmd)
            output_path = utils.replace_argument(self.options, '$WORKSPACE/portscan/html-report/{0}-html.html'.format(ip))
            std_path = utils.replace_argument(self.options, '$WORKSPACE/portscan/html-report/std-{0}-html.std'.format(ip))
            execute.send_cmd(cmd, output_path, std_path, self.module_name)



    ###disable because this take really long time :v
    # def eyewitness_all(self):
    #     utils.print_good('Starting EyeWitness for all protocol')
    #     cmd = 'python $PLUGINS_PATH/EyeWitness/EyeWitness.py -x  $WORKSPACE/portscan/$OUTPUT-masscan.xml --web --all-protocols --prepend-https --threads 20 -d $WORKSPACE/screenshot/all/'  
    #     cmd = utils.replace_argument(self.options, cmd)
    #     utils.print_info("Execute: {0} ".format(cmd))
    #     print()
    #     # execute.run_as_background(cmd)

