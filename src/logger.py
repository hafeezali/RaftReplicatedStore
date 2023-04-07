import logging
import os


class Logging:
    def __init__(self, server_id):
        self.log_level = logging.DEBUG
        # Logger name is set to server id
        server_id = server_id.replace("'", "")
        self.logger = logging.getLogger(server_id)

        log_folder_path = '/home/logs_dir'
        os.path.dirname(log_folder_path)
        if not os.path.exists(log_folder_path):
            os.makedirs(log_folder_path)
        self.log_file_name = f'{log_folder_path}/{server_id}_exec_logs.txt'
        

    def get_logger(self):
        logging.basicConfig(filename=self.log_file_name, 
                            level=self.log_level,
                            format='%(asctime)s : %(name)s : {%(pathname)s:%(funcName)s:%(lineno)d} : %(message)s', 
                            datefmt='%d-%b-%y %H:%M:%S',
                            filemode='w')

        return self.logger