"""
ec2_shutdown.py - Terminate EC2 instance to save costs
"""

import boto3
import sys
from pathlib import Path


def terminate_instance(instance_id: str) -> bool:
    """
    Terminate EC2 instance
    
    Args:
        instance_id: EC2 instance ID
        
    Returns:
        True if successful
    """
    ec2 = boto3.client('ec2')
    
    try:
        # Get instance details before terminating
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        instance_type = instance['InstanceType']
        state = instance['State']['Name']
        
        print(f"Instance: {instance_id}")
        print(f"Type: {instance_type}")
        print(f"Current state: {state}")
        
        if state == 'terminated':
            print("\n✅ Instance already terminated")
            return True
        
        # Confirm termination
        print(f"\n⚠️  This will TERMINATE instance {instance_id}")
        print("This action cannot be undone!")
        
        confirm = input("Type 'terminate' to confirm: ")
        
        if confirm.lower() != 'terminate':
            print("❌ Termination cancelled")
            return False
        
        # Terminate
        print(f"\n🔄 Terminating instance {instance_id}...")
        ec2.terminate_instances(InstanceIds=[instance_id])
        
        print("✅ Termination initiated")
        print("Instance will shut down in ~30 seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def terminate_saved_instance() -> bool:
    """Terminate instance from .instance_id file"""
    instance_file = Path('.instance_id')
    
    if not instance_file.exists():
        print("❌ No saved instance ID found")
        print("Run: python ec2_shutdown.py <instance-id>")
        return False
    
    instance_id = instance_file.read_text().strip()
    
    if not instance_id:
        print("❌ Saved instance ID is empty")
        return False
    
    print(f"Found saved instance: {instance_id}")
    success = terminate_instance(instance_id)
    
    if success:
        # Remove saved instance file
        instance_file.unlink()
        print(f"\nRemoved: {instance_file}")
    
    return success


def terminate_all_cctv_instances():
    """Find and terminate all CCTV analysis instances"""
    ec2 = boto3.client('ec2')
    
    # Find instances with CCTV tags
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Project', 'Values': ['CCTV-Analysis']},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
        ]
    )
    
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances.append({
                'id': instance['InstanceId'],
                'type': instance['InstanceType'],
                'state': instance['State']['Name'],
                'ip': instance.get('PublicIpAddress', 'N/A')
            })
    
    if not instances:
        print("No running CCTV instances found")
        return True
    
    print(f"\nFound {len(instances)} CCTV instance(s):")
    for i, inst in enumerate(instances, 1):
        print(f"  {i}. {inst['id']} ({inst['type']}) - {inst['state']} - IP: {inst['ip']}")
    
    print(f"\n⚠️  This will TERMINATE all {len(instances)} instance(s)")
    confirm = input("Type 'terminate all' to confirm: ")
    
    if confirm.lower() != 'terminate all':
        print("❌ Termination cancelled")
        return False
    
    # Terminate all
    instance_ids = [inst['id'] for inst in instances]
    print(f"\n🔄 Terminating {len(instance_ids)} instance(s)...")
    
    ec2.terminate_instances(InstanceIds=instance_ids)
    
    print("✅ Termination initiated for all instances")
    
    return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Terminate EC2 instance')
    parser.add_argument('instance_id', nargs='?', help='Instance ID to terminate')
    parser.add_argument('--all', action='store_true', 
                       help='Terminate all CCTV instances')
    
    args = parser.parse_args()
    
    print("="*60)
    print("EC2 Instance Termination")
    print("="*60)
    print()
    
    if args.all:
        success = terminate_all_cctv_instances()
    elif args.instance_id:
        success = terminate_instance(args.instance_id)
    else:
        success = terminate_saved_instance()
    
    if success:
        print("\n" + "="*60)
        print("✅ Termination Complete")
        print("="*60)
        print("\n💰 Instance will stop incurring charges within 1 minute")
        print("💡 Launch a new instance with: python ec2_startup.py")
        return 0
    else:
        print("\n❌ Termination failed or cancelled")
        return 1


if __name__ == '__main__':
    exit(main())