from setuptools import setup

package_name = 'nexus_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Chaud-FS',
    maintainer_email='chaud-fs@example.com',
    description='Visual perception node powered by Qwen-VL.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'qwen_vl_node = nexus_perception.qwen_vl_node:main',
        ],
    },
)
