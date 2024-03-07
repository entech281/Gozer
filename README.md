# Gozer
A build server for the robot cart

# installation
 * install python 3.9.x or higher
 * install jdk v 17 
 * install wpilib for your platform
 * clone project to the location you would like. make sure this location doesnt have code you could lose--this repo wil lbe hard reset during deploys
 * set origin of the git clone to git@10.2.81.10, (gitea)
 * copy gozer.ini.sample to gozer.ini, and change values to point to the above
 * run 'git config --global pager.branch false'
 * change into the git repo, and run:
```
git branch -r | grep -v '\->' | sed "s,\x1B\[[0-9;]*[a-zA-Z],,g" | while read remote; do git branch --track "${remote#origin/}" "$remote"; done
git fetch --all
git pull --all
```
 * run a gradle build while connected to internet:
```./gradlew build```

 * gnow run another build in offline mode to cache dependenices
```commandline
./gradlew --offline build
```

 * set up the systemd service ( ubuntu 22 instructions):
 ```
 sudo cp gozer.systemd /etc/systemd/system/gozer.service
 sudo systemctl daemon-reload
 sudo systemctl enable gozer
 sudo systemctl start gozer
 ```
 
 If it doesnt work, view the logs like this:
 ```sudo journalctl -r -u gozer.service
     
 
# Troublehsooting
Here are commands that will help

# Future Improvements
* continuously check for rio and gitea, and dont allow build when not there
* also show a status so we can see which is connected easily
* collapsible log sections to hide details
* toggle debug logging from the main panel
* gather up all the git_commands module level vars and functions into a class
* add ability to call commands
* move configuratoin into the gui rather than filesystem  
    * ip of gitea
    * debug
    * etc
