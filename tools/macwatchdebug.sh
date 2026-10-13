#!/bin/bash
# (temporary: what sloppy watch does on a Mac, with the stacks of its processes when it hangs)
export SLOPPY_LIB=$PWD/lib SLOPPY_SOFTWARE=1 SLOPPY_FRAMES=1000000 SLOPPY_WATCH_DEBUG=1
d=$(mktemp -d); cd $d
printf 'x = 0.0\nupdate = (dt: f64):\n    x += 2.0\n    if int(x) %% 40 == 2: print("tick x={x} label={label()}")\ndraw = ():\n    clear(vec4(0, 0, 0, 1))\nlabel = () -> str: "one"\n' > g.jo
sleep 100 | SLOPPY_SCREENSHOT=$d/shot.png $OLDPWD/bin/sloppy watch g.jo > out.txt 2>&1 &
sleep 6
sed -i '' 's/"one"/"two"/' g.jo
sleep 6
grep -v '^tick' out.txt | head -20
echo "--- ticks:"; grep '^tick' out.txt | tail -3
for p in $(pgrep -f 'sloppy|watch-'); do echo "=== $p: $(ps -o command= -p $p | cut -c1-80)"; sample $p 1 2>/dev/null | grep -E '^ +[0-9]+ ' | head -25; done
pkill -f 'sloppy watch'; true
