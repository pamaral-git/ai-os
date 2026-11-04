export PATH="$HOME/.local/bin:$HOME/.local/share/uv/tools/bin:$HOME/.grok/bin:/Users/pedroamaral/.antigravity-ide/antigravity-ide/bin:$PATH"
export PATH="$HOME/.bun/bin:$PATH"
export DO_NOT_TRACK=1
alias osh="openshell"
export OMP_TELEMETRY=0

[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"

fpath=(
  /Users/pedroamaral/.docker/completions
  $fpath
)
autoload -Uz compinit && compinit -C

eval "$(mise activate zsh)"

# bun completions
[ -s "/Users/pedroamaral/.bun/_bun" ] && source "/Users/pedroamaral/.bun/_bun"

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/pedroamaral/miniconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/pedroamaral/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/pedroamaral/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/pedroamaral/miniconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

