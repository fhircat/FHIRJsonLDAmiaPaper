# See original source code at https://github.com/fhircat/fhir_rdf_validator/blob/master/fhir_rdf_validator/json_to_r4.py

import os
import sys
import urllib
from argparse import Namespace, ArgumentParser
from typing import Any, List, Optional, Union, Dict, Tuple
from urllib.parse import quote

import dirlistproc
import requests
from jsonasobj import JsonObj, loads, as_dict, as_json
from rdflib import URIRef, XSD

from fhir_url_re import R5_FHIR_URI_RE
from fsv_processor import FSVProcessor, FHIR
from rdf_postprocessor import gYear_re, gYearMonth_re, date_re, dateTime_re

# For internal debugging.  Should be an empty list for submission
INCLUDE_ONLY = []

DEFAULT_CONTEXT_SERVER = "https://fhircat.org/fhir-r5/original/contexts/"

CODE_SYSTEM_MAP = {
    "http://snomed.info/sct": "sct",
    "http://loinc.org": "loinc"
}

# Maximum size of input file to process -- bypass the really big monsters
MAX_JSON = 50000000

# The conversion process depends on these JSON keys
VALUE_KEY = "value"             # This is the key we inject into the JSON to make it look like the RDF/XML
                                # Note that from_value assumes that there aren't spurious values in the JSON
SYSTEM_KEY = "system"           # Coding system name
CODE_KEY = "code"               # code
REFERENCE_KEY = "reference"     # assumed to always point to a partial or full URL
                                # Not true:  In particular, the Consent resource has a 'reference' of type 'Reference'
TYPE_KEY = "type"               # If reference is present, "type" (if present) names the type of the target resource

RESOURCETYPE_KEY = "resourceType"  # Changes the type of the current resource being analyzed
ID_KEY = "id"                   # All resources have to have both a type and an id. Id is the resource IRI
CONTAINED_KEY = "contained"     # Contained resources in root

# Keys that aren't converted to value objetsc
NODEROLE_KEY = "nodeRole"       # nodeRole is one WE add, We don't use value notation
INDEX_KEY = "index"             # index is one we add (although there appears to be a couple of native values)
DIV_KEY = "div"                 # div is not converted to value as per the spec

CODING_KEY = "coding"           # Assumption is that ALL "coding" entries carry concept codes and that all entries are
                                # lists

VALUE_KEY = 'value'
VALUE_KEY_LEN = len(VALUE_KEY)

EXTENSION_RESOURCE_TYPE = "Extension"

BUNDLE_RESOURCE_TYPE = "Bundle"
BUNDLE_ENTRY = "entry"
BUNDLE_ENTRY_FULLURL = "fullUrl"
BUNDLE_ENTRY_RESOURCE = "resource"


def to_value(v: Any) -> JsonObj:
    """ Convert v to {"value": v} """
    return JsonObj(**{VALUE_KEY: v})


def from_value(v: Any) -> Any:
    """ Extract the actual value from v noting that it may have already been transformed using to_value

        Note: This assumes that we aren't going to find a "value" in native FHIR JSON.  If this turns out not
              to be the case, we should probably use a safe token (say, "V") during the processing and then
              transform it as a final step.
    """
    return v[VALUE_KEY] if isinstance(v, JsonObj) and VALUE_KEY in as_dict(v) else v


def local_name(tag: str) -> str:
    """
    Remove the namespace prefix from tag if it has been added
    :param tag: simple name or ns:name
    :return: name
    """
    return tag if tag is None or not tag.startswith('fhir:') else tag[len('fhir:'):]


def add_date_type(date_type: URIRef, container: JsonObj) -> None:
    """
    Add the appropriate type to container
    :param date_type: FHIR date/time type
    :param container: Target container
    """
    date_str = from_value(container)
    dt = None
    if date_type in (FHIR.date, FHIR.dateTime):
        if gYear_re.match(date_str):
            dt = XSD.gYear
        elif gYearMonth_re.match(date_str):
            dt = XSD.gYearMonth
        elif date_re.match(date_str):
            dt = XSD.date
        elif date_type == FHIR.dateTime and dateTime_re.match(date_str):
            dt = XSD.dateTime
    if dt:
        typed_obj = JsonObj()
        typed_obj['@value'] = date_str
        typed_obj['@type'] = str(dt)
        container['value'] = typed_obj


def add_type_arc(codedobject: JsonObj) -> None:
    """
    Add a type arc to a coded concept
    :param codedobject: Recipient of arc
    """
    if hasattr(codedobject, SYSTEM_KEY) and hasattr(codedobject, CODE_KEY):
        system = from_value(codedobject[SYSTEM_KEY])
        code = quote(from_value(codedobject[CODE_KEY]), safe='')
        system_root = system[:-1] if system[-1] in '/#' else system
        if system_root in CODE_SYSTEM_MAP:
            base = CODE_SYSTEM_MAP[system_root] + ':'
        else:
            base = system + ('' if system[-1] in '/#' else '/')
        codedobject['@type'] = base + urllib.parse.quote(code, safe='')


def add_type_arcs(element_key: str, container: JsonObj, parent_container: JsonObj, path: List[str], opts: Namespace,
                  server: str, id_map: Optional[Dict[str, str]]) -> None:
    """
    Add type arcs if element_key is "code", "reference" or a type of canonical

    :param element_key: Key to test
    :param container: Object to add the arcs to
    :param parent_container: Object that holds the container.  This is because the FHIR R4 RDF puts the link in the
        parent of a reference key, not the value
    :param path: Path to object
    :param opts: Holder for the FSVProcessor element (opts.fsv)
    :param server:
    :param id_map: Map from relative to absolute URI's
    """
    ref = None
    if opts.fsv.is_canonical(path):
        # Container is a simple string in this case
        ref = gen_reference(from_value(container), container, server, id_map)
        container["fhir:link"] = ref
    elif element_key == REFERENCE_KEY:
        container_value = from_value(container)
        if isinstance(container_value, str):
            ref = gen_reference(container_value, container, server, id_map)
            parent_container["fhir:link"] = ref

    date_type = opts.fsv.is_date(path)
    if date_type:
        add_date_type(date_type, container)

    if element_key == CODE_KEY:
        add_type_arc(container)


def gen_reference(ref: str, refobject: JsonObj, server: Optional[str], id_map: Optional[Dict[str, str]])\
        -> Optional[JsonObj]:
    """
    Return the object of a fhir:link based on the reference in refObject

    :param ref: reference
    :param refobject: object containing the reference
    :param server: If supplied,
    :param id_map: Map of bundle reference names to URI/type tuples
    :return: link and optional type element
    """
    if "://" not in ref and not ref.startswith('/'):  # Relative path
        link = ('' if server else '../') + ref        # If server is supplied, ref is local, else relative to parent
    else:
        link = ref
    if link:
        if hasattr(refobject, TYPE_KEY):
            typ = refobject[TYPE_KEY]
        else:
            # TODO: we need to decide whether to use R5 or R4 regular expressions here
            m = R5_FHIR_URI_RE.match(ref)
            typ = m[4] if m else None

        rval = JsonObj()

        if link in id_map:
            rval['@id'] = id_map[link]
        else:
            rval['@id'] = link
            if typ:
                rval['@type'] = "fhir:" + typ
        return rval
    return None


def add_contained_urls(resource: JsonObj, id_map: Dict[str, str]) -> None:
    """
    Return a map of contained resources to absolute URL's

    :param resource: resource that may have contained entries
    :param id_map: map of relative URL's to absolute url and type
    """

    containers = getattr(resource, CONTAINED_KEY, [])

    for container in containers:
        contained_id = '#' + getattr(container, ID_KEY)
        contained_type = getattr(resource, RESOURCETYPE_KEY)
        id_map[contained_id] = contained_type + '/' + getattr(resource, ID_KEY) + contained_id


def bundle_urls(resource: JsonObj) -> Optional[Dict[str, Tuple[str, str]]]:
    """
    Return a map of relative bundle URL's to absolute URLs, assigning full URL's to interior entries as well
    :param resource: Resource to be mapped
    :return: Map from local identifier to URL/Type tuple
    """
    rt = getattr(resource, RESOURCETYPE_KEY, None)
    if rt != BUNDLE_RESOURCE_TYPE:
        return None

    rval = dict()
    entries = getattr(resource, BUNDLE_ENTRY, None)
    if entries:
        for entry in entries:
            fullUrl = getattr(entry, BUNDLE_ENTRY_FULLURL, None)
            if fullUrl:
                resource = getattr(entry, BUNDLE_ENTRY_RESOURCE, None)
                if resource:
                    resource['@id'] = fullUrl
                    resource_id = getattr(resource, ID_KEY, None)
                    resource_type = getattr(resource, RESOURCETYPE_KEY, None)
                    if resource_id:
                        rval[resource_type + '/' + resource_id] = fullUrl
    return rval


def adjust_urls(fhir_json: Any, outer_url: Optional[str] = "") -> None:
    """
    Traverse the structure adding relative URL's to inner structures
    :param fhir_json:
    :param outer_url: Containing URL
    :return:
    """
    if isinstance(fhir_json, JsonObj):
        if hasattr(fhir_json, '@id'):
            container_id = getattr(fhir_json, '@id')
            if str(container_id).startswith('#'):
                container_id = outer_url + container_id
                fhir_json['@id'] = container_id
            outer_url = container_id
        for k in as_dict(fhir_json).keys():
            adjust_urls(fhir_json[k], outer_url)
    elif isinstance(fhir_json, list):
        for e in fhir_json:
            adjust_urls(e, outer_url)


def to_r4(fhir_json: JsonObj, opts: Namespace, ifn: str) -> JsonObj:
    """
    Convert the FHIR Resource in "o" into the R4 value notation

    :param fhir_json: FHIR resource
    :param opts: command line parser arguments
    :param ifn: input file name
    :return: reference to "o" with changes applied.  Warning: object is NOT copied before change
    """
    server = opts.fhirserver            # If absent, the FILE becomes the base of the context

    def is_choice_element(name):
        # TODO: we really do need to be a lot more clever if this is to scale in the longer term.  For now, we
        # assume that valueX is a choice unless it is an exception
        return name.startswith(VALUE_KEY) and name[VALUE_KEY_LEN:] and name[VALUE_KEY_LEN].isupper() and\
               name[VALUE_KEY_LEN:] not in ['Set']


    def map_element(element_key: str, element_value: Any, container_type: str, path: List[str],
                    container: JsonObj, id_map: Optional[Dict[str, str]] = None, in_container: bool = False) -> None:
        """
        Transform element_value into the R4 RDF json structure

        :param element_key: Key for element value
        :param element_value: Element itself.  Can be any JSON object
        :param container_type: The type of the containing resource
        :param path: The path from the containing resource down to the element excluding element_key
        :param container: Dictionary that contains key/value
        :param id_map: Map from local resource to URI if inside a bundle
        :param in_container: True means don't tack the resource type onto the identifier
        """
        if element_key.startswith('@'):  # Ignore JSON-LD components
            return

        if not is_choice_element(element_key):
            path.append(element_key)
        if path == ['Coding', 'system']:
            add_type_arc(container)
        inner_type = local_name(getattr(container, RESOURCETYPE_KEY, None))
        if isinstance(element_value, JsonObj):          # Inner object -- process each element
            dict_processor(element_value, resource_type, path, id_map)

        elif isinstance(element_value, list):           # List -- process each member individually
            container[element_key] = list_processor(element_key, element_value, resource_type, path, id_map)

        # We have a primitive JSON value
        elif element_key == RESOURCETYPE_KEY and not element_value.startswith('fhir:'):
            container[element_key] = 'fhir:' + element_value
            container['@context'] = f"{opts.contextserver}{element_value.lower()}.context.jsonld"

        elif element_key == ID_KEY:     # Internal ids are relative to the document
            if in_container or getattr(container, RESOURCETYPE_KEY, None) is None:
                relative_id = '#' + element_value
            else:
                relative_id = element_value if element_value.startswith('#') else \
                            ((inner_type or container_type) + '/' + element_value)
            container_id = id_map.get(relative_id, relative_id) if id_map else relative_id
            if not hasattr(container, '@id'):
                # Bundle ids have already been added elsewhere
                container['@id'] = container_id
            container[element_key] = to_value(element_value)

        elif element_key not in [NODEROLE_KEY, INDEX_KEY, DIV_KEY]:      # Convert most other nodes to value entries
            container[element_key] = to_value(element_value)

        if not isinstance(element_value, list):
            add_type_arcs(element_key, container[element_key], container, path, opts, server, id_map)

        if not is_choice_element(element_key):
            path.pop()

    def dict_processor(container: JsonObj, resource_type: Optional[str] = None, path: List[str] = None,
                       id_map: Optional[Dict[str, str]] = None, in_container: bool = False) -> None:
        """
        Process the elements in container

        :param container: JSON dictionary to be processed
        :param resource_type: type of resource that container appears in
        :param path: Full path from the base resource type to the actual element
        :param id_map: Map from local resource to URI if inside a bundle
        :param in_container: If True then don't tack they type onto the identifier
        """

        # Rule: Whenever we find an embedded resourceType, we assume that we've encountered a brand new resource
        #       Update the passed resource type (example: container is Observation, we're processing the subject node
        #       and the inner resourceType is Patient
        #
        # Note: If there isn't a declared resourceType, it may be able to be extracted from the URL if the URL matches
        #       the predefined FHIR structure
        if hasattr(container, RESOURCETYPE_KEY):
            resource_type = container[RESOURCETYPE_KEY]
            path = [resource_type]

        # If we've got bundle, build an id map to use in the interior
        possible_id_map = bundle_urls(container)            # Note that this will also assign ids to bundle entries
        if possible_id_map is not None:
            id_map = possible_id_map
        elif id_map is None:
            id_map = dict()

        # Add any contained resources to the contained URL map
        add_contained_urls(container, id_map)

        # Process each of the elements in the dictionary
        # Note: use keys() and re-look up to prevent losing the JsonObj characteristics of the values
        for k in [k for k in as_dict(container).keys() if not k.startswith('_')]:
            if is_choice_element(k):
                map_element(k, container[k], resource_type, [k[VALUE_KEY_LEN:]], container, id_map, in_container)
            else:
                map_element(k, container[k], resource_type, path, container, id_map, in_container)

        # Merge any extensions (keys that start with '_') into the base
        #  This happens when either:
        #     A) there is only an extension and no base
        #     B) there is a base, but it isn't a JSON object
        for ext_key in [k for k in as_dict(container).keys() if k.startswith('_')]:
            base_key = ext_key[1:]
            ext_value = container[ext_key]
            del(container[ext_key])

            if not hasattr(container, base_key):
                container[base_key] = ext_value                 # No base -- move the extension in
            elif not isinstance(container[base_key], JsonObj):
                container[base_key] = to_value(container[base_key])     # Base is not a JSON object
                container[base_key]['extension'] = ext_value['extension'] \
                    if isinstance(ext_value, JsonObj) else ext_value
            else:
                container[base_key]['extension'] = ext_value['extension']

            map_element(base_key, ext_value, EXTENSION_RESOURCE_TYPE, [EXTENSION_RESOURCE_TYPE], container, id_map)

    def list_processor(list_key: str, list_object: List[Any], resource_type: str, path: List[str] = None,
                       id_map: Optional[Dict[str, str]] = None) -> List[Any]:
        """
        Process the elements in the supplied list adding indices and doing an iterative transformation on the
        interior nodes

        :param list_key: JSON key at the start of the list
        :param list_object: List to be processed
        :param resource_type: The type of resource containing the list
        :param path: JSON path to list element.  Head of path is the root resource type
        :param id_map: Map from local resource to URI if inside a bundle

        :return Ordered list of entries
        """

        def list_element(entry: Any, pos: int) -> Any:
            """
            Add a list index to list element "e"

            :param entry: Element in a list
            :param pos: position of element
            :return: adjusted object
            """
            if isinstance(entry, JsonObj):
                dict_processor(entry, resource_type, path, id_map, list_key == CONTAINED_KEY)
                if getattr(entry, INDEX_KEY, None) is not None and '_' not in opts.fsv.flat_path(path):
                    print(f'{ifn} - problem: "{list_key}: {opts.fsv.flat_path(path)}" element {pos} already has an index')
                else:
                    entry.index = pos               # Add positioning
                if list_key == CODING_KEY:
                    add_type_arc(entry)
            elif isinstance(entry, list):
                print(f"{ifn} - problem: {list_key} has a list in a list")
            else:
                entry = to_value(entry)
                add_type_arcs(list_key, entry, entry, path, opts, server, id_map)
                entry.index = pos
            return entry

        return [list_element(list_entry, pos) for pos, list_entry in enumerate(list_object)]

    # =========================
    # Start of to_r4 base code
    # =========================

    # Do the recursive conversion
    resource_type = fhir_json[RESOURCETYPE_KEY]     # Pick this up before it processed for use in context below
    dict_processor(fhir_json)

    # Add nodeRole
    fhir_json['nodeRole'] = "fhir:treeRoot"

    # Traverse the graph adjusting relative URL's
    adjust_urls(fhir_json)

    # Add the "ontology header"
    hdr = JsonObj()
    if '@id' in fhir_json:
        hdr["@id"] = fhir_json['@id'] + ".ttl"
        hdr["owl:versionIRI"] = (opts.versionbase + ('' if opts.versionbase[-1] == '/' else '') +
                                 hdr['@id']) if opts.versionbase else hdr["@id"]
        hdr["owl:imports"] = "fhir:fhir.ttl"
        hdr["@type"] = 'owl:Ontology'
        fhir_json["@included"] = hdr
    else:
        print(f"{ifn} does not have an identifier")

    # Fill out the rest of the context
    if opts.addcontext:
        fhir_json['@context'] = [f"{opts.contextserver}{resource_type.lower()}.context.jsonld"]
        fhir_json['@context'].append(f"{opts.contextserver}root.context.jsonld")
        local_context = JsonObj()
        local_context["nodeRole"] = JsonObj(**{"@type": "@id", "@id": "fhir:nodeRole"})
        if server:
            local_context["@base"] = server
        local_context['owl:imports'] = JsonObj(**{"@type": "@id"})
        local_context['owl:versionIRI'] = JsonObj(**{"@type": "@id"})
        fhir_json['@context'].append(local_context)
    return fhir_json


def convert_file(ifn: str, ofn: str, opts: Namespace) -> bool:
    """
    Convert ifn to ofn

    :param ifn: Name of file to convert
    :param ofn: Target file to convert to
    :param opts: Parameters AND in_json, which contains the JSON representation of the file to convert

    :return: True if conversion is successful
    """
    if ifn not in opts.converted_files:
        out_json = to_r4(opts.in_json, opts, ifn)
        with open(ofn, "w") as outf:
            outf.write(as_json(out_json))
        opts.converted_files.append(ifn)
    return True


def check_json(ifn: str, ifdir: str, opts: Namespace) -> bool:
    """
    This process is called once per candidate file.  If it returns True, the file should be converted.  False means
    skip. If the file should be processed, its JSON representation is tacked onto opts as in_json to prevent re-parsing

    :param ifn: file name or URL
    :param ifdir: containing directory
    :param opts: options namespace.  Here so we can tack on the JSON representation of the file to eliminate the need
        to re-parse it if accepted
    :return: True if file should be processed
    """
    # Input file name can be a URL
    if '://' in ifn:
        infilename = ifn
        resp = requests.get(ifn)
        if not resp.ok:
            print(f"Error {resp.status_code}: {ifn} {resp.reason}")
            return False
        intext = resp.text
    else:
        infilename = os.path.join(ifdir, ifn)
        with open(infilename) as infile:
            intext = infile.read()

    if len(intext) > MAX_JSON:
        print(f"{infilename} is too big {len(intext)}")
        return False

    # Internal testing
    if INCLUDE_ONLY and not any(ifn.startswith(e) for e in INCLUDE_ONLY):
        return False

    in_json = loads(intext)
    if not (hasattr(in_json, RESOURCETYPE_KEY) or hasattr(in_json, ID_KEY)):
        print(f"{infilename} is not a FHIR resource - processing skipped")
        return False
    print(f"Processing {infilename}")
    opts.in_json = in_json

    return True


def addargs(parser: ArgumentParser) -> None:
    parser.add_argument("-c", "--addcontext", help="Add JSON-LD context references", action="store_true")
    parser.add_argument("-fs", "--fhirserver", help="FHIR server base")
    parser.add_argument("-cs", "--contextserver", help="Context server base",
                        default=DEFAULT_CONTEXT_SERVER)
    parser.add_argument("-vb", "--versionbase", help="Base URI for OWL version. Default: fhirserver")


def main(argv: Optional[Union[str, List[str]]] = None) -> object:
    """
    Apply R4 edits to FHIR JSON files

    :param argv: Argument list.  Can be unparsed string, a list of strings or nothing. If nothing, we use sys.argv
    :return: 0 if all RDF files that had valid FHIR in them were successful, 1 otherwise
    """
    def gen_dlp(args: List[str]) -> dirlistproc.DirectoryListProcessor:
        return dirlistproc.DirectoryListProcessor(args, "Add FHIR R4 edits to JSON file", '.json', '.json',
                                                  addargs=addargs)

    if INCLUDE_ONLY:
        print("=====> WARNING: json preprocessor is configured to process a subset")
    dlp = gen_dlp(argv)
    if not (dlp.opts.infile or dlp.opts.indir):
        gen_dlp(argv if argv is not None else sys.argv[1:] + ["--help"])  # Does not exist

    dlp.opts.converted_files = []           # If converting inline

    # Note: we don't supply a FSVProcessor if we're working with a single file.  May need to fix if issues arise
    dlp.opts.fsv = FSVProcessor(os.path.join(os.path.dirname(dlp.opts.indir), 'fhir.ttl')) if dlp.opts.indir else None

    nfiles, nsuccess = dlp.run(convert_file, file_filter_2=check_json)
    print(f"Total={nfiles} Successful={nsuccess}")

    return 0 if nfiles == nsuccess else 1


if __name__ == '__main__':
    main()
