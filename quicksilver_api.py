def quicksilver_tasks():
    return [
        ('check_task_completion', '--no-color', 300,),
        ('check_qualtrics_tasks', '--no-color', 3600,),
        ('update_amazon_task_metadata', '--no-color', 900,),
        ('update_data_point_metadata', '--no-color', 900,),
        ('update_pilot_data_status', '--no-color', 900,),
    ]
