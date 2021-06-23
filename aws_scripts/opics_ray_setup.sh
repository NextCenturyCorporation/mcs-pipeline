ray up -y autoscaler/ray_opics_aws.yaml
ray rsync_up -v autoscaler/ray_opics_aws.yaml configs/ '~/configs/'
ray rsync_up -v autoscaler/ray_opics_aws.yaml deploy_files/opics/ '~'
ray rsync_up -v autoscaler/ray_opics_aws.yaml pipeline '~'
#ray rsync_up -v autoscaler/ray_opics_aws.yaml scenes_single_scene.txt '~'
ray submit autoscaler/ray_opics_aws.yaml pipeline_ray.py configs/opics_aws.ini configs/mcs_config_opics_oracle.ini