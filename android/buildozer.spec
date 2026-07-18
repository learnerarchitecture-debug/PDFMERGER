[app]
title = PDF Merger & Splitter
package.name = pdfmerger
package.domain = org.pdfmerger
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,ttf,txt
version = 1.0.0
requirements = python3,kivy==2.3.1,plyer,PyMuPDF,Pillow
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.3.1
fullscreen = 0

# Android specific
android.api = 34
android.minapi = 21
android.ndk = 27c
android.sdk = 34
android.gradle_dependencies = 'com.android.support:appcompat-v7:28.0.0'
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES
android.accept_sdk_license = True
android.allow_backup = True
android.AndroidManifest_xml = 
android.add_src = 
android.add_jars = 
android.add_libs_arm64 = 
android.add_libs_armv7a = 
android.add_libs_x86 = 
android.add_libs_x86_64 = 
android.archs = arm64-v8a
android.wakelock = False
android.library_receivers = 
android.ndk_path = 
android.sdk_path = 
android.ant_path = 
android.java_path = 
android.gradle_path = 
android.storage_path = 
android.private_storage_path = 
android.copy_libs = 
android.google_play_services = 
android.clean_on_stop = 0

# iOS specific
ios.codesign.allowed = 
ios.codesign.debug = 
ios.codesign.release = 

# presplash
presplash.filename = 
icon.filename = 

# Meta
author = 
description = Merge and split PDF files on your Android device.
