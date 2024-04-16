# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac
color_prompt=yes

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    markup_git_branch() {
      if [[ -n $@ ]]; then
        if [[ -z $(git status --porcelain 2> /dev/null) ]]; then
          echo -e "[$@ \001\033[32;1m\002●\001\033[0m\002]"
        else
          echo -e "[$@ \001\033[31;1m\002●\001\033[0m\002]"
        fi
      fi
    }
    parse_git_branch() {
      git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e 's/* (*\([^)]*\))*/\1/'
    }

    export PS1="\[\033[00;32m\]\u:\[\033[01;34m\]\w \[\033[38;2;222;211;184m\]\$(markup_git_branch \$(parse_git_branch))\[\033[31;1m\]⟩\[\033[32;1m\]⟩\[\033[33;1m\]⟩\[\033[0m\] "
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=00;32:locus=01:quote=01'

# some more ls aliases
alias ll='ls -alF --color'
alias la='ls -A --color'
alias l='ls -CF --color'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

[ -f ~/.fzf.bash ] && source ~/.fzf.bash

# enable bash-git-prompt
#GIT_PROMPT_ONLY_IN_REPO=1
#source ~/.bash-git-prompt/gitprompt.sh

# git functions
git-reset(){
    local current_branch="$(git branch --show-current)"
    echo "Reset soft from $current_branch to $1 branch..."

    git fetch
    git pull
    git switch $1
    git pull
    git switch $current_branch
    git reset --soft $1
}

git-push(){
    echo "Pulling..."
    git pull
    git add -A
    git status
    echo "Do you want to continue? (Y/N)"
    read proceed
    if [[ $proceed == "Y" || $proceed == "y" || $proceed == "" ]]; then
        git commit -m "$1"
        echo "Pushing..."
        git push
    elif [[ $proceed == "N" || $proceed == "n" ]]; then
        echo "Operation cancelled."
    else
        echo "Invalid input. Operation cancelled."
    fi
}

# This solves windows slow git on ntfs filesystem
# checks to see if we are in a windows or linux dir
function isWinDir {
  case $PWD/ in
    /mnt/*) return $(true);;
    *) return $(false);;
  esac
}
# wrap the git command to either run windows git or linux
function git {
  if isWinDir
  then
    git.exe "$@"
  else
    /usr/bin/git "$@"
  fi
}

# Start bc weith pi defined
alias bc='bc -v; bc -lq <(echo "pi=5*a(1)")'

# When leaves ranger keeps in current directory
alias ranger='ranger --choosedir=$HOME/.rangerdir; LASTDIR=`cat $HOME/.rangerdir`; cd "$LASTDIR"'

# Pretty Git log
function git_tably () {
    unset branch_all graph_all hash_all message_all time_all max_chars

    ### add here the same code as under "2) as a shell-script" ###
        # Edit your color/style preferences here or use empty values for git auto style
    tag_style="1;38;5;222"
    head_style="1;3;5;1;38;5;196"
    branch_style="38;5;214"

    # Determine the max character length of your git tree
    while IFS=+ read -r graph;do
      chars_count=$(sed -nl1000 'l' <<< "$graph" | grep -Eo '\\\\|\||\/|\ |\*|_' | wc -l)
      [[ $chars_count -gt ${max_chars:-0} ]] && max_chars=$chars_count
    done < <(cd "${1:-"$PWD"}" && git log --all --graph --pretty=format:' ')

    # Create the columns for your preferred table-like git graph output
    while IFS=+ read -r graph hash time branch message;do

      # Count needed amount of white spaces and create them
      whitespaces=$(($max_chars-$(sed -nl1000 'l' <<< "$graph" | grep -Eo '\\\\|\||\/|\ |\*|_' | wc -l)))
      whitespaces=$(seq -s' ' $whitespaces|tr -d '[:digit:]')

      # Show hashes besides the tree ...
      #graph_all="$graph_all$graph$(printf '%7s' "$hash")$whitespaces \n"

      # ... or in an own column
      graph_all="$graph_all$graph$whitespaces\n"
      hash_all="$hash_all$(printf '%7s' "$hash")  \n"

      # Format all other columns
      time_all="$time_all$(printf '%12s' "$time") \n"
      branch=${branch//1;32m/${branch_style:-1;32}m}
      branch=${branch//1;36m/${head_style:-1;36}m}
      branch=${branch//1;33m/${tag_style:-1;33}m}
      branch_all="$branch_all$(printf '%15s' "$branch")\n"
      message_all="$message_all$message\n"

    done < <(cd "${1:-"$PWD"}" && git log --all --graph --decorate=short --color --pretty=format:'+%C(bold 214)%<(7,trunc)%h%C(reset)+%C(dim white)%>(12,trunc)%cr%C(reset)+%C(auto)%>(15,trunc)%D%C(reset)+%C(white)%s%C(reset)' && echo);

    # Paste the columns together and show the table-like output
    paste -d' ' <(echo -e "$time_all") <(echo -e "$branch_all") <(echo -e "$graph_all") <(echo -e "$hash_all") <(echo -e "$message_all")
}
