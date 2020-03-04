import jsonld from 'jsonld'
import fs from 'fs'
import optimist from 'optimist'

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
    .demand(['c', 'i'])

const argv = opts.argv

const content = fs.readFileSync(argv.input).toString()
let options = {}
if (argv.context) {
    options['expandContext'] = argv.context
} else if (argv.frame) {
    options = JSON.parse(fs.readFileSync(argv.frame).toString())
}
const command = argv.command
if (command in jsonld && typeof jsonld[command] === 'function') {
    jsonld[command](JSON.parse(content), options).then(val => {
        if (argv.output) {
            fs.writeFileSync(argv.output, JSON.stringify(val, null, 2))
        } else {
            console.log(JSON.stringify(val, null, 2))
        }
    }).catch(error => console.log(error, error.message))
}
