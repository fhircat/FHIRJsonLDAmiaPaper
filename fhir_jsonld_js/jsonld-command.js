import jsonld from 'jsonld'
import fs from 'fs'
import optimist from 'optimist'
import path from 'path'

const opts = optimist.usage('$0: A command line JSONLD script')
    .describe('i', 'JSON file to process')
    .alias('i', 'input')
    .describe('o', 'Output file')
    .alias('o', 'output')
    .describe('c', 'Command: expand, frame or compact')
    .alias('c', 'command')
    .describe('x', 'JSONLD Context')
    .alias('x', 'context')
    .describe('f', 'frame file')
    .alias('f', 'frame')
    .describe('n', 'Input directory')
    .alias('n', 'indir')
    .describe('m', 'Output directory')
    .alias('m', 'outdir')
    .demand(['c'])

let invalidUrls = new Set()

const runCommand = (command, input, output=null, options={}) => {
    const content = fs.readFileSync(input).toString()
    if (command in jsonld && typeof jsonld[command] === 'function') {
        jsonld[command](JSON.parse(content), options).then(val => {
            if (output) {
                fs.writeFileSync(output, JSON.stringify(val, null, 2))
            } else {
                console.log(JSON.stringify(val, null, 2))
            }
        }).catch(error => {
            if (error.name === 'jsonld.InvalidUrl') {
                invalidUrls.add(error.details.url)
                console.log(invalidUrls)
            }
            //console.log(error, error.message)
        })
    }
};

const argv = opts.argv;
let options = {};
if (argv.context) {
    options['expandContext'] = argv.context
} else if (argv.frame) {
    options = JSON.parse(fs.readFileSync(argv.frame).toString())
}
if (argv.indir && argv.outdir) {
    let indir = path.resolve(process.cwd(), argv.indir);
    let outdir = path.resolve(process.cwd(), argv.outdir);
    fs.readdirSync(indir)
        .filter(file => (file.indexOf('.') !== 0))
        .forEach(file => {
            let inputFile = path.join(indir, file);
            let outputFile = path.join(outdir, file);
            runCommand(argv.command, inputFile, outputFile, options);
        });
    console.log(invalidUrls);
} else {
    runCommand(argv.command, argv.input, argv.output, options)
}


