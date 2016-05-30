#!/usr/bin/python
# 
# tm_status.py - A Python script for displaying what Time Machine is currently doing. 
#
# v1.0, 2016-05-29: Initial release. 
# 
# MIT License
# 
# Copyright (c) 2016 Vincent Tagle
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import plistlib
import subprocess
import os
import time
import datetime
import errno

# Given the time remaining in seconds, return a description of it. 
#
def time_left(seconds_remaining):
	time_left = ""
	
	if seconds_remaining < 0:
		time_left = "Unknown"
	elif seconds_remaining < 10:
		time_left = "A few seconds..."
	elif seconds_remaining < 60:
		time_left = "%d seconds." % seconds_remaining
	elif seconds_remaining < 120:
		time_left = "About a minute."
	else:
		time_left = "%d minutes." % (seconds_remaining / 60)
	
	return time_left

# Print out the current phase progress. 
#
def display_progress(seconds_remaining, percent_completed):
	if seconds_remaining > 0:
		print "* Time remaining: %s" % time_left(seconds_remaining)
	
	print "* Percent completed: %.0f%%." % percent_completed

plist = None
plist_string = None

# Run tmutil with the specified arguments and return the output as a string. 
#
def tmutil_output(arguments):
	output = ""
	error_code = 0
	
	try:
		command = ['tmutil'] + arguments
		out_bytes = subprocess.check_output(command, stderr=subprocess.STDOUT)
		output = out_bytes.decode('utf-8')
	except subprocess.CalledProcessError as e:
		out_bytes = e.output
		output = out_bytes.decode('utf-8')
		error_code = e.returncode
	
	return (output.strip(), error_code)

# Check if there's a test XML file specified and use that for the plist data.
#
if len(sys.argv) > 1:
	try:
		plist = plistlib.readPlist(sys.argv[1])
	except IOError as e:
		print "Unable to read plist file."
		exit()
# No XML file specified for input so get it from tmutil. 
# 
else:
	plist_string, error_code = tmutil_output(['status', '-X'])
	if error_code == 0:
		plist = plistlib.readPlistFromString(plist_string)
	else:
		print "tmutil exited with code: %d" % code
		print plist_string

if plist != None:
	# Verify that Time Machine is running a backup. 
	#
	if plist.get("Running", False):
		# Display where Time Machine is backing up to. 
		#
		destination = plist.get("DestinationMountPoint", "Unknown destination")
		print "Time Maching backing up to %s:" % os.path.basename(destination)
		
		# Get the values for the current progress with error defaults. 
		#
		progress = plist.get("Progress", {"TimeRemaining": -1})
		seconds_remaining = int(progress.get("TimeRemaining", -1))
		
		# Not sure what the difference between Percent and _raw_Percent is but
		# the latter seems to be more accurate. 
		#
		percent = plist.get("_raw_Percent", 0.0)
		percent_completed = float(percent) * 100.0
		
		# Display the current progress depending on the backup phase. 
		#
		backupPhase = plist.get("BackupPhase", "Unknown")
		if backupPhase == "Copying":
			print "* Phase: Copying files..."
			display_progress(seconds_remaining, percent_completed)
		elif backupPhase == "Starting":
			print "* Phase: Starting backup..."
		elif backupPhase == "ThinningPreBackup":
			print "* Phase: Determining items to copy..."
		elif backupPhase == "Finishing":
			print "* Phase: Finishing up backup..." 
		elif backupPhase == "ThinningPostBackup":
			print "* Phase: Cleaning up..."
			display_progress(seconds_remaining, percent_completed)
		# Handle any phase we didn't know about. 
		#
		else:
			# Make sure there's a directory to store the log file we're about to create. 
			#
			log_directory = os.path.expanduser("~/tm_status logs/")
			
			try:
				os.makedirs(log_directory)
			except OSError as exception:
				if exception.errno != errno.EEXIST:
					raise
			
			# Filename based on the current date and time. 
			#
			now = datetime.datetime.now()
			now_str = now.strftime("tmutil %Y-%m-%d %H-%M-%S.txt")
			output_path = log_directory + now_str
			
			# Save the log file and indicate where it went. 
			#
			with open(output_path, 'w') as file:
				file.write(plist_string)
			
			print "Unknown backup phase. Dumping tmutil output to %s" % (output_path)
	# No backup running so find out if we can display the date and time of the
	# last backup. 
	#
	else:
		print "Time Machine currently inactive."
		
		if len(sys.argv) == 1:
			latestbackup_output, error_code = tmutil_output(['latestbackup'])
			
			if os.path.exists(latestbackup_output):
				latest_backup = os.path.basename(latestbackup_output)
				latest_backup_datetime = datetime.datetime.strptime(latest_backup, "%Y-%m-%d-%H%M%S")
				latest_backup_display = latest_backup_datetime.strftime("%b %d, %Y at %I:%M %p")
				
				print "Latest backup: %s." % latest_backup_display
			else:
				# latestbackup returns an error code of 1 if it can't find a backup 
				# destination. 
				#
				if error_code == 1:
					print "No backup destinations available."
				else:
					print "tmutil exited with code %d" % error_code
					print latestbackup_output
	
# Uh, something went wrong with our input sources...
#
else:
	print "Unable to determine Time Machine status."
