from setuptools import setup

package_name = 'nexus_voice'

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
    description='Voice interaction module for the Nexus assistant.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'stt_node = nexus_voice.stt_node:main',
            'tts_node = nexus_voice.tts_node:main',
        ],
    },
)
