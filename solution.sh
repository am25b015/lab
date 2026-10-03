# 1. Sort numbers.txt in ascending order
sort -n numbers.txt

# 2. Print the IP address of the machine (alternative to hostname -I)
ip addr show | grep "inet " | awk '{print $2}' | cut -d/ -f1

# 3. Show contents of readme.txt
less -FX readme.txt

# 4. Count lines in data.csv (alternative to wc -l)
awk 'END {print NR}' data.csv

# 5. Find all files containing the word "error" in logs folder
find logs -type f -exec grep -H "error" {} \;

# 6. Display last 10 lines of app.log
tail -n 10 app.log

# 7. Make script.sh executable for everyone
chmod 755 script.sh

# 8. Search for "TODO" in every .py file in current directory
grep -n "TODO" ./*.py

# 9. Show the last 20 commands from history
history 20

# 10. Show processes sorted by memory usage
top -o %MEM -b -n 1 | head -20

# 11. Find all directories named "backup" anywhere on system
find / -type d -name backup 2>/dev/null

# 12. Replace "foo" with "bar" in example.txt and save to new_example.txt
tr ' ' '\n' < example.txt | sed 's/foo/bar/g' | tr '\n' ' ' > new_example.txt


